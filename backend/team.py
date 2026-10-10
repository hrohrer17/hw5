"""The Campus Customs agent team: Boss, Inventory, Accounting, Facilities, Customer Service.

- Five PydanticAI agents, all on gpt-6-luna (config.build_model).
- Shop facts and changes come only from the campus-customs MCP server. Each agent sees just the
  MCP tools on its TOOL_ACCESS list; nobody gets approve_payment.
- Full connectivity: every agent has a `delegate` tool that can hand a task to any other agent,
  including the Boss. Guards stop loops: no hand-off back into the current chain, a depth cap,
  and a per-ticket delegation cap. All agents in a run share one usage counter and limit.
- Every agent-loop step is appended to output/audit_trail.json (audit.py).

Entry point: `await run_ticket(101)` returns a TicketRunResult.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.usage import RunUsage
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from audit import AuditTrail
from config import (
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    MCP_SERVER,
    MODEL_NAME,
    MODEL_SETTINGS,
    TICKET_USAGE_LIMITS,
    build_model,
    load_prompt,
    mcp_server_env,
)
from models import (
    AGENT_TITLES,
    AGENTS,
    TOOL_ACCESS,
    AgentName,
    Delegation,
    TicketOutcome,
    TicketRunResult,
)

REQUEST_TOOLS = {"request_invoice_payment", "request_rent_payment", "request_purchase_order"}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- run state


@dataclass
class RunState:
    """Shared by every agent working one ticket run."""

    run_id: str
    ticket_id: int
    audit: AuditTrail
    agents: dict[str, Agent] = field(default_factory=dict)
    delegations: list[Delegation] = field(default_factory=list)

    def log(self, agent: str, depth: int, step: int | None, event: str, **detail: Any) -> None:
        self.audit.append(run_id=self.run_id, ticket_id=self.ticket_id, agent=agent, depth=depth,
                          step=step, event=event, **detail)


@dataclass
class TeamDeps:
    """Per agent-run context: who is running, how deep in the hand-off chain, and the shared state."""

    agent: AgentName
    depth: int
    chain: tuple[AgentName, ...]
    state: RunState


# ---------------------------------------------------------------- MCP connection


def _mcp_toolset() -> MCPToolset:
    """One stdio connection to the campus-customs MCP server, shared by all five agents in a run."""
    # keep_alive=False: the server process ends with the run instead of lingering (FastMCP's default keeps it)
    transport = StdioTransport(command=sys.executable, args=[str(MCP_SERVER)], env=mcp_server_env(), keep_alive=False)
    return MCPToolset(Client(transport), process_tool_call=_stamp_requester)


async def _stamp_requester(ctx: RunContext[TeamDeps], call_tool, name: str, args: dict[str, Any]):
    """Payment requests are always filed under the agent that really made them."""
    if name in REQUEST_TOOLS:
        args = {**args, "requested_by": AGENT_TITLES[ctx.deps.agent]}
    return await call_tool(name, args)


# ---------------------------------------------------------------- delegation (full connectivity)


async def delegate(ctx: RunContext[TeamDeps], to_agent: AgentName, task: str) -> str:
    """Hand a focused task to a teammate and get their answer back.

    Any agent can call any other agent: boss, inventory, accounting, facilities, customer_service.
    Give a self-contained task that says what you need and why (include SKUs, sizes, quantities,
    invoice or lease ids, and amounts you already know). The teammate uses their own tools and
    replies in plain text.

    Args:
        to_agent: Who should do it: boss, inventory, accounting, facilities, or customer_service.
        task: What you need from them, written so they can act without asking you questions.
    """
    deps = ctx.deps
    state = deps.state
    record = Delegation(from_agent=deps.agent, to_agent=to_agent, task=task, depth=deps.depth + 1)

    refusal = None
    if to_agent == deps.agent:
        refusal = "You can't delegate to yourself. Do the work with your own tools."
    elif to_agent in deps.chain:
        refusal = (f"{AGENT_TITLES[to_agent]} is already waiting on this hand-off chain "
                   f"({' -> '.join(AGENT_TITLES[a] for a in deps.chain)}). Finish with what you have "
                   "and put any open question in your reply.")
    elif deps.depth + 1 > MAX_DELEGATION_DEPTH:
        refusal = f"Hand-off chains are capped at {MAX_DELEGATION_DEPTH} deep. Answer with what you have."
    elif len(state.delegations) >= MAX_DELEGATIONS_PER_TICKET:
        refusal = f"This ticket has used all {MAX_DELEGATIONS_PER_TICKET} hand-offs. Answer with what you have."

    if refusal:
        record.refused = refusal
        state.delegations.append(record)
        state.log(deps.agent, deps.depth, None, "delegation_refused", to_agent=to_agent, task=task, reason=refusal)
        return f"[hand-off refused] {refusal}"

    state.delegations.append(record)
    state.log(deps.agent, deps.depth, None, "delegation", to_agent=to_agent, task=task)

    child = TeamDeps(agent=to_agent, depth=deps.depth + 1, chain=(*deps.chain, to_agent), state=state)
    prompt = (f"Ticket {state.ticket_id}. {AGENT_TITLES[deps.agent]} has handed you this task:\n\n{task}\n\n"
              "Do it with your tools and reply in plain text to "
              f"{AGENT_TITLES[deps.agent]}.")
    reply = await run_logged(to_agent, prompt, child, usage=ctx.usage, output_type=str)
    record.reply = reply
    state.log(deps.agent, deps.depth, None, "delegation_reply", from_agent=to_agent, reply=reply)
    return reply


# ---------------------------------------------------------------- agents


def build_team(toolset: MCPToolset) -> dict[str, Agent]:
    """Create all five agents. Each gets its own prompt, its slice of the MCP tools, and `delegate`."""
    team: dict[str, Agent] = {}
    for name in AGENTS:
        allowed = TOOL_ACCESS[name]
        team[name] = Agent(
            build_model(),
            name=name,
            instructions=load_prompt(name),
            deps_type=TeamDeps,
            output_type=TicketOutcome if name == "boss" else str,
            toolsets=[toolset.filtered(lambda ctx, tool, allowed=allowed: tool.name in allowed)],
            tools=[delegate],
            model_settings=MODEL_SETTINGS,
            retries=2,
        )
    return team


async def run_logged(agent_name: AgentName, prompt: str, deps: TeamDeps, *, usage=None, output_type=None):
    """Run one agent's loop, appending every step to the audit trail as it happens."""
    state = deps.state
    agent = state.agents[agent_name]
    state.log(agent_name, deps.depth, 0, "agent_start", prompt=prompt)
    step = 0
    kwargs: dict[str, Any] = {"deps": deps, "usage": usage, "usage_limits": TICKET_USAGE_LIMITS}
    if output_type is not None:
        kwargs["output_type"] = output_type

    async with agent.iter(prompt, **kwargs) as run:
        async for node in run:
            if not (Agent.is_model_request_node(node) or Agent.is_call_tools_node(node) or Agent.is_end_node(node)):
                continue
            step += 1
            if Agent.is_model_request_node(node):
                # What goes to the model this step: the prompt, or results of the tools it called.
                parts = []
                for p in node.request.parts:
                    if isinstance(p, ToolReturnPart):
                        parts.append({"tool_result": p.tool_name, "content": p.content})
                    elif isinstance(p, RetryPromptPart):
                        parts.append({"retry": p.tool_name, "content": p.content})
                    elif isinstance(p, UserPromptPart):
                        parts.append({"user_prompt": p.content})
                state.log(agent_name, deps.depth, step, "model_request", parts=parts)
            elif Agent.is_call_tools_node(node):
                # What the model decided this step: text and/or tool calls, plus token use.
                resp = node.model_response
                calls = [{"tool": p.tool_name, "args": p.args_as_dict()} for p in resp.parts
                         if isinstance(p, ToolCallPart)]
                text = "\n".join(p.content for p in resp.parts if isinstance(p, TextPart)).strip()
                # model = what we asked for (always gpt-6-luna). Portkey reports its deployment name
                # for the same model (e.g. "gpt-6-luna-global"), kept separately for the record.
                state.log(agent_name, deps.depth, step, "model_response", model=MODEL_NAME,
                          provider_model=resp.model_name, text=text or None, tool_calls=calls,
                          tokens={"input": resp.usage.input_tokens, "output": resp.usage.output_tokens})
            elif Agent.is_end_node(node):
                output = node.data.output
                shown = output.model_dump() if hasattr(output, "model_dump") else output
                state.log(agent_name, deps.depth, step, "agent_finish", output=shown)
        return run.result.output


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


async def run_ticket(ticket_id: int, audit: AuditTrail | None = None, run_id: str | None = None) -> TicketRunResult:
    """Run the whole team on one ticket, starting with the Boss."""
    state = RunState(run_id=run_id or new_run_id(), ticket_id=ticket_id, audit=audit or AuditTrail())
    result = TicketRunResult(run_id=state.run_id, ticket_id=ticket_id, model=MODEL_NAME, started_at=_now())
    state.log("system", 0, None, "run_start", model=MODEL_NAME,
              limits={"requests": TICKET_USAGE_LIMITS.request_limit,
                      "tool_calls": TICKET_USAGE_LIMITS.tool_calls_limit,
                      "total_tokens": TICKET_USAGE_LIMITS.total_tokens_limit,
                      "max_delegation_depth": MAX_DELEGATION_DEPTH,
                      "max_delegations": MAX_DELEGATIONS_PER_TICKET})

    toolset = _mcp_toolset()
    usage = RunUsage()
    try:
        async with toolset:  # one MCP server process for the whole run
            state.agents = build_team(toolset)
            boss = TeamDeps(agent="boss", depth=0, chain=("boss",), state=state)
            prompt = (f"Work ticket {ticket_id}. Read it, decide who on the team should handle which part, "
                      "delegate, make the final call, set the ticket's status, and return the outcome.")
            result.outcome = await run_logged("boss", prompt, boss, usage=usage)
    except UsageLimitExceeded as exc:
        result.error = f"Stopped by the cost limit: {exc}"
    except Exception as exc:  # the trail must show why a run died
        result.error = f"{type(exc).__name__}: {exc}"
    result.finished_at = _now()
    result.delegations = state.delegations
    result.usage = {"requests": usage.requests, "tool_calls": usage.tool_calls,
                    "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens}
    state.log("system", 0, None, "run_finish", error=result.error, usage=result.usage,
              final_status=result.outcome.final_status if result.outcome else None,
              outcome=result.outcome.model_dump() if result.outcome else None)
    return result
