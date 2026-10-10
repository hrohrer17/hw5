"""Data types shared by the agent team (and, later, the API and the dashboard)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENTS: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

AGENT_TITLES: dict[str, str] = {
    "boss": "Boss",
    "inventory": "Inventory",
    "accounting": "Accounting",
    "facilities": "Facilities",
    "customer_service": "Customer Service",
}

# Which MCP tools each agent may call (least privilege). approve_payment and decline_payment are
# on no list: only a human can move money.
TOOL_ACCESS: dict[str, frozenset[str]] = {
    "boss": frozenset({
        "list_tickets", "get_ticket", "get_cash_balance", "list_payment_requests", "update_ticket_status",
    }),
    "inventory": frozenset({
        "get_ticket", "check_stock_and_pricing", "list_stock_for_sku", "list_vendors", "get_vendor_invoice",
    }),
    "accounting": frozenset({
        "get_ticket", "get_cash_balance", "get_vendor_invoice", "get_lease_rent_due",
        "check_stock_and_pricing", "list_vendors", "list_payment_requests",
        "request_invoice_payment", "request_rent_payment", "request_purchase_order",
    }),
    "facilities": frozenset({
        "get_ticket", "get_lease_rent_due", "get_cash_balance", "list_payment_requests",
    }),
    "customer_service": frozenset({
        "get_ticket", "check_stock_and_pricing", "list_stock_for_sku", "list_vendors", "list_payment_requests",
    }),
}


class AgentContribution(BaseModel):
    agent: AgentName
    contribution: str = Field(description="One or two sentences on what this agent did on the ticket.")


class ApprovalNeeded(BaseModel):
    request_id: int = Field(description="payment_requests.id returned by the request tool")
    kind: Literal["invoice", "rent", "purchase_order"]
    payee: str
    amount: float
    why: str = Field(description="Why the shop should pay this, in one sentence.")


class TicketOutcome(BaseModel):
    """What the Boss hands back at the end of a ticket run."""

    ticket_id: int
    final_status: Literal["resolved", "waiting_on_approval", "in_progress"] = Field(
        description="Must match the status the Boss set with update_ticket_status."
    )
    outcome: str = Field(description="Two or three plain-English sentences on how the ticket ends.")
    boss_decision: str = Field(description="The Boss's final call and the reason for it.")
    contributions: list[AgentContribution] = Field(description="One entry per agent that worked the ticket.")
    approvals_needed: list[ApprovalNeeded] = Field(
        default_factory=list, description="Pending payment requests a human must approve or decline."
    )
    customer_message_draft: str | None = Field(
        default=None, description="Draft from Customer Service for the requester. Never sent by the agents."
    )
    follow_ups: list[str] = Field(default_factory=list, description="Anything left for a human or a later day.")


class Delegation(BaseModel):
    from_agent: AgentName
    to_agent: AgentName
    task: str
    depth: int
    reply: str | None = None
    refused: str | None = None


class TicketRunResult(BaseModel):
    run_id: str
    ticket_id: int
    model: str
    started_at: str
    finished_at: str | None = None
    outcome: TicketOutcome | None = None
    delegations: list[Delegation] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
