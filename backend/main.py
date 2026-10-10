"""Campus Customs desk API: the routes the React dashboard calls.

Start it from the backend/ folder:   uvicorn main:app --reload --port 8000

Routes
  GET  /tickets                      the three tickets, each with status, open/resolved, and pending payments
  POST /tickets/{ticket_id}/run      run the agent team on one ticket (in the background; ?wait=true blocks)
  GET  /events                       recent agent events from the audit trail (?after=, ?ticket_id=, ?run_id=, ?limit=)
  POST /payments/{request_id}/approve  a human approves a prepared payment; the only route that moves cash
  GET  /cash                         checking balance from cash_accounts
  POST /reset                        copy the original database over the working copy for a fresh run

CORS allows the Vite dev page (http://localhost:5173) to call these routes.
Shop data is read and changed through the campus-customs MCP server, the same one the agents use.
The only exception is /reset, which is a file copy.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic import BaseModel, Field

from audit import AuditTrail
from config import AUDIT_TRAIL, MCP_SERVER, MODEL_NAME, ORIGINAL_DB, mcp_server_env, working_db
from models import AGENT_TITLES, TicketRunResult
from team import new_run_id, run_ticket

audit = AuditTrail()


class DeskState:
    """In-memory state for this server process: the MCP connection and the current/last runs."""

    def __init__(self) -> None:
        self.mcp: Client | None = None
        self.mcp_lock = asyncio.Lock()
        self.current: dict[str, Any] | None = None       # {"run_id", "ticket_id", "started_at"}
        self.task: asyncio.Task | None = None
        self.last_results: dict[int, TicketRunResult] = {}


desk = DeskState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One long-lived connection to the MCP server for the routes (agent runs open their own).
    # keep_alive=False so the server process exits when the API shuts down (FastMCP keeps it by default)
    client = Client(StdioTransport(command=sys.executable, args=[str(MCP_SERVER)], env=mcp_server_env(),
                                   keep_alive=False))
    async with client:
        desk.mcp = client
        yield
    desk.mcp = None


app = FastAPI(title="Campus Customs desk API", lifespan=lifespan)

# The React board runs on Vite's dev server; let the browser call these routes from that page.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


async def mcp(tool: str, **args: Any) -> dict:
    """Call one campus-customs MCP tool and return its result."""
    if desk.mcp is None:
        raise HTTPException(503, "MCP server is not connected.")
    async with desk.mcp_lock:
        result = await desk.mcp.call_tool(tool, args, raise_on_error=False)
    if result.is_error:
        raise HTTPException(502, f"MCP tool {tool} failed: {result.content}")
    return result.structured_content or {}


def _running() -> bool:
    return desk.task is not None and not desk.task.done()


# ---------------------------------------------------------------- tickets


def _read_trail() -> list[dict]:
    try:
        return json.loads(AUDIT_TRAIL.read_text(encoding="utf-8")) if AUDIT_TRAIL.exists() else []
    except json.JSONDecodeError:
        return []  # writes are atomic, so this means a damaged file; audit.py moves it aside on next write


def _last_runs_from_trail(entries: list[dict]) -> dict[int, dict]:
    """Latest finished run per ticket since the last reset, rebuilt from the audit trail.

    Lets the board show outcomes after a backend restart (the in-memory results are gone then).
    """
    since = max((i for i, e in enumerate(entries) if e.get("event") == "db_reset"), default=-1)
    runs: dict[int, dict] = {}
    for e in entries[since + 1:]:
        if e.get("event") == "run_finish" and isinstance(e.get("ticket_id"), int):
            runs[e["ticket_id"]] = {
                "run_id": e["run_id"], "finished_at": e["ts"], "error": e.get("error"),
                "outcome": e.get("outcome"), "usage": e.get("usage"),
                "delegations": [
                    {"from_agent": d["agent"], "to_agent": d.get("to_agent"), "task": d.get("task"),
                     "depth": d.get("depth", 0) + 1, "refused": d.get("reason")}
                    for d in entries[since + 1:]
                    if d.get("run_id") == e["run_id"] and d.get("event") in ("delegation", "delegation_refused")
                ],
            }
    return runs


@app.get("/tickets")
async def list_tickets() -> dict:
    """The tickets with their status, a simple open/resolved state, and any payments waiting on a human."""
    data = await mcp("list_tickets")
    pending = (await mcp("list_payment_requests", status="pending"))["requests"]
    from_trail = _last_runs_from_trail(_read_trail())
    tickets = []
    for t in data["tickets"]:
        last = desk.last_results.get(t["id"])
        tickets.append({
            **t,
            "state": "resolved" if t["status"] == "resolved" else "open",
            "pending_requests": [r for r in pending if r["ticket_id"] == t["id"]],
            "running": _running() and desk.current["ticket_id"] == t["id"],
            "last_run": from_trail.get(t["id"]) if last is None else {
                "run_id": last.run_id,
                "finished_at": last.finished_at,
                "error": last.error,
                "outcome": last.outcome.model_dump() if last.outcome else None,
                "delegations": [d.model_dump() for d in last.delegations],
                "usage": last.usage,
            },
        })
    return {"shop_date_today": data["shop_date_today"], "running": desk.current if _running() else None,
            "tickets": tickets}


async def _run_and_store(ticket_id: int, run_id: str) -> TicketRunResult:
    result = await run_ticket(ticket_id, audit=audit, run_id=run_id)
    desk.last_results[ticket_id] = result
    return result


@app.post("/tickets/{ticket_id}/run")
async def run_ticket_route(ticket_id: int, wait: bool = False) -> dict:
    """Start the agent team on one ticket. Returns at once with a run_id; watch progress on /events.

    One run at a time: the team shares one cash balance, and this also caps spending.
    """
    if _running():
        raise HTTPException(409, f"Ticket {desk.current['ticket_id']} is already running (run {desk.current['run_id']}).")
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found"):
        raise HTTPException(404, f"No ticket {ticket_id}.")

    run_id = new_run_id()
    desk.current = {"run_id": run_id, "ticket_id": ticket_id, "model": MODEL_NAME}
    desk.task = asyncio.create_task(_run_and_store(ticket_id, run_id))
    if not wait:
        return {"started": True, "run_id": run_id, "ticket_id": ticket_id, "model": MODEL_NAME}
    result = await desk.task
    return {"started": True, **result.model_dump()}


# ---------------------------------------------------------------- events


def _summary(e: dict) -> str:
    """One readable line per audit entry for the board."""
    who = AGENT_TITLES.get(e.get("agent"), e.get("agent", ""))
    ev = e.get("event")
    if ev == "agent_start":
        return f"{who} picked up the task."
    if ev == "model_response":
        calls = ", ".join(c["tool"] for c in e.get("tool_calls") or [])
        said = (e.get("text") or "").strip()
        if said and calls:
            return f"{who}: {said[:300]} (calling {calls})"
        return f"{who} is calling {calls}" if calls else f"{who}: {said[:300]}"
    if ev == "model_request":
        results = [p["tool_result"] for p in e.get("parts", []) if "tool_result" in p]
        return f"{who} got results from {', '.join(results)}" if results else f"{who} is thinking."
    if ev == "delegation":
        return f"{who} → {AGENT_TITLES.get(e.get('to_agent'), e.get('to_agent'))}: {e.get('task', '')[:300]}"
    if ev == "delegation_reply":
        return f"{AGENT_TITLES.get(e.get('from_agent'), e.get('from_agent'))} replied to {who}."
    if ev == "delegation_refused":
        return f"Hand-off from {who} blocked: {e.get('reason', '')}"
    if ev == "agent_finish":
        return f"{who} finished."
    if ev == "run_start":
        return f"Run started on ticket {e.get('ticket_id')} ({e.get('model')})."
    if ev == "run_finish":
        return (f"Run finished: {e.get('final_status') or 'no outcome'}"
                + (f", error: {e['error']}" if e.get("error") else "") + ".")
    if ev == "human_approval":
        return f"{e.get('approved_by')} approved ${e.get('amount')} to {e.get('payee')}."
    if ev == "db_reset":
        return "Working database reset to the original values."
    return ev or ""


@app.get("/events")
async def events(after: int = Query(-1, description="Only events with seq greater than this"),
                 ticket_id: int | None = None, run_id: str | None = None,
                 limit: int = Query(200, ge=1, le=1000)) -> dict:
    """Recent agent events (what each agent did, said, and which tools it used), read from the audit trail.

    Poll with ?after=<last seq you saw> to get only new events.
    """
    entries = _read_trail()
    out = []
    for seq, e in enumerate(entries):
        if seq <= after:
            continue
        if ticket_id is not None and e.get("ticket_id") != ticket_id:
            continue
        if run_id is not None and e.get("run_id") != run_id:
            continue
        out.append({"seq": seq, "summary": _summary(e), **e})
    out = out[-limit:]
    return {"last_seq": len(entries) - 1, "running": desk.current if _running() else None, "events": out}


# ---------------------------------------------------------------- money


class Approval(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human approving the payment")


@app.post("/payments/{request_id}/approve")
async def approve_payment(request_id: int, body: Approval) -> dict:
    """A human approves one prepared payment or purchase order. This is the only route that moves cash.

    If it was the ticket's last pending payment, the ticket moves from waiting_on_approval to resolved.
    """
    result = await mcp("approve_payment", request_id=request_id, approved_by=body.approved_by)
    if not result.get("approved"):
        reason = result.get("refused", "Not approved.")
        raise HTTPException(404 if reason.startswith("No payment request") else 409, reason)

    ticket_update = None
    tid = result.get("ticket_id")
    if tid is not None and result.get("ticket_pending_requests_left") == 0:
        ticket = await mcp("get_ticket", ticket_id=tid)
        if ticket.get("status") == "waiting_on_approval":
            ticket_update = await mcp(
                "update_ticket_status", ticket_id=tid, status="resolved",
                note=f"{body.approved_by} approved payment {result['payment_id']} "
                     f"(${result['amount']:,.2f} to {result['payee']}); nothing left pending.",
            )
    audit.append(run_id="human", ticket_id=tid, agent="human", depth=0, step=None, event="human_approval",
                 request_id=request_id, approved_by=body.approved_by, amount=result["amount"],
                 payee=result["payee"], kind=result["kind"], checking_before=result["checking_before"],
                 checking_after=result["checking_after"], updated=result["updated"],
                 ticket_resolved=bool(ticket_update and ticket_update.get("updated")))
    return {**result, "ticket_update": ticket_update}


@app.get("/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts, plus what is promised to pending requests."""
    return await mcp("get_cash_balance")


# ---------------------------------------------------------------- reset


@app.post("/reset")
async def reset() -> dict:
    """Copy data/campus_customs.db over the working copy so the next run starts fresh.

    The audit trail is kept (it is append-only); a db_reset entry marks the point.
    """
    if _running():
        raise HTTPException(409, "A ticket is running. Wait for it to finish before resetting.")
    target = working_db()
    shutil.copyfile(ORIGINAL_DB, target)  # overwrites contents; the original stays read-only
    desk.last_results.clear()
    balance = await mcp("get_cash_balance")
    audit.append(run_id="human", ticket_id=None, agent="human", depth=0, step=None, event="db_reset",
                 source=ORIGINAL_DB.name, target=target.name, checking_after_reset=balance["balance"])
    return {"reset": True, "database": target.name, "copied_from": ORIGINAL_DB.name,
            "checking_balance": balance["balance"]}
