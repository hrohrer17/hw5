"""campus-customs: a FastMCP server that gives the Campus Customs agents facts from the shop database.

Every answer comes straight from data/campus_customs_new.db (the working copy). Nothing is made up:
if a row isn't in the database, the tool says it wasn't found. Day counts are worked out from the
shop's own date, desk.date_today, never the real calendar.

Money rules enforced here, not just in the agent prompts:
- Agents can only *request* a payment (request_* tools). A request never moves cash.
- Only a human can approve one (approve_payment), which writes the payments row, lowers the
  checking balance, and updates the table that was paid (invoice -> paid, lease -> next month).
- A request or approval that would push checking below $0 is refused. Cash only goes out.

Run with stdio (the vibe coder starts it):  python mcp_server/server.py
Set CAMPUS_DB_PATH to point the server at a different copy (used for test runs).
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from fastmcp import FastMCP

# Resolved from this file so the server finds the database no matter where it is launched from.
DB_PATH = Path(
    os.getenv("CAMPUS_DB_PATH")
    or Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
)

# Role names the agents use. A payment can't be approved under one of these names.
AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer service", "customer_service"}
TICKET_STATUSES = ("open", "in_progress", "waiting_on_approval", "resolved")

mcp = FastMCP(
    "campus-customs",
    instructions=(
        "Facts about the Campus Customs shop, read from data/campus_customs_new.db. "
        "Only report what these tools return; never invent stock, prices, invoices or dates. "
        "'Today' for the shop is desk.date_today, not the real date. "
        "Agents may request payments; only a human approves them (approve_payment)."
    ),
)

# Pending payments and purchase orders wait here for a human. The original database doesn't have
# this table, so it is created on first use (and disappears again when the working copy is reset).
_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,             -- invoice | rent | purchase_order
    ref_id INTEGER,                 -- invoice id, lease id, or vendor id (purchase orders)
    payee TEXT NOT NULL,
    amount REAL NOT NULL,
    sku TEXT, size TEXT, qty INTEGER,
    ticket_id INTEGER,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,           -- pending | approved | declined
    created_at TEXT NOT NULL,
    decided_by TEXT, decided_at TEXT, decision_note TEXT, payment_id INTEGER
)
"""


@contextmanager
def _db(write: bool = False):
    """Open the database, commit if this was a write that finished cleanly, and always close."""
    if write:
        conn = sqlite3.connect(DB_PATH)
    else:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        if write:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _shop_today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _add_one_month(day: str) -> str:
    d = date.fromisoformat(day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    for dd in (d.day, 30, 29, 28):  # clamp e.g. Jan 31 -> Feb 28
        try:
            return date(year, month, dd).isoformat()
        except ValueError:
            continue
    raise ValueError(day)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _has_requests_table(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='payment_requests'"
    ).fetchone() is not None


def _pending_total(conn: sqlite3.Connection) -> float:
    if not _has_requests_table(conn):
        return 0.0
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_requests WHERE status = 'pending'"
    ).fetchone()[0]


def _checking(conn: sqlite3.Connection) -> sqlite3.Row:
    return conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()


def _open_request_for(conn: sqlite3.Connection, kind: str, ref_id: int) -> sqlite3.Row | None:
    if not _has_requests_table(conn):
        return None
    return conn.execute(
        "SELECT id, status FROM payment_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'",
        (kind, ref_id),
    ).fetchone()


def _file_request(conn, *, kind, ref_id, payee, amount, reason, requested_by, ticket_id,
                  sku=None, size=None, qty=None) -> dict:
    """Shared last step of every request_* tool: cash check, then insert a pending request."""
    checking = _checking(conn)
    pending = _pending_total(conn)
    available = round(checking["balance"] - pending, 2)
    if amount > available:
        return {
            "created": False,
            "refused": "Not enough cash. The checking balance can never go negative.",
            "amount": amount,
            "checking_balance": checking["balance"],
            "already_pending": pending,
            "available_after_pending": available,
        }
    conn.execute(_REQUESTS_TABLE)
    cur = conn.execute(
        """INSERT INTO payment_requests
           (kind, ref_id, payee, amount, sku, size, qty, ticket_id, reason, requested_by, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (kind, ref_id, payee, amount, sku, size, qty, ticket_id, reason, requested_by, _now()),
    )
    return {
        "created": True,
        "request_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "payee": payee,
        "amount": amount,
        "note": "Waiting for a human to approve. No cash has moved.",
        "checking_balance": checking["balance"],
        "available_after_this_request": round(available - amount, 2),
    }


# ---------------------------------------------------------------- read-only look-ups


@mcp.tool
def list_tickets() -> dict:
    """List every ticket on the desk: type, requester, subject, status, notes, and its links.

    Reads the tickets and desk tables. Start here to see what is open.
    """
    with _db() as conn:
        rows = conn.execute(
            """SELECT id, type, requester, subject, status, created_at, notes,
                      sku, size, qty, lease_id, invoice_id FROM tickets ORDER BY id"""
        ).fetchall()
        today = _shop_today(conn)
    return {"shop_date_today": today, "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Read one ticket in full: requester, request notes, and its links (sku/size/qty, lease_id, invoice_id).

    Reads the tickets and desk tables. Empty link fields are null; follow the filled ones with the
    stock, invoice, or lease tools.
    """
    with _db() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"found": False, "error": f"No ticket with id {ticket_id}."}
        today = _shop_today(conn)
    return {"found": True, **dict(row), "shop_date_today": today}


@mcp.tool
def check_stock_and_pricing(sku: str, size: str) -> dict:
    """Look up how many units of one product size are on the shelf, plus its unit cost and list price.

    Reads the inventory and pricing tables. Use it to see whether an order can be filled from stock
    and how much margin there is before discussing any discount. Sizes are S, M, L, XL, or OS.
    """
    with _db() as conn:
        stock = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        price = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()

    if stock is None:
        return {"found": False, "error": f"No inventory row for SKU {sku} size {size}."}

    result = {"found": True, **dict(stock)}
    if price is None:
        result["pricing"] = f"No pricing row for SKU {sku}."
    else:
        result["unit_cost"] = price["unit_cost"]
        result["list_price"] = price["list_price"]
        result["margin_per_unit"] = round(price["list_price"] - price["unit_cost"], 2)
    return result


@mcp.tool
def list_stock_for_sku(sku: str) -> dict:
    """Show stock for every size of one product, plus its unit cost and list price.

    Reads the inventory and pricing tables. Use it to find other sizes that could fill or partly
    fill an order when the requested size is short.
    """
    with _db() as conn:
        rows = conn.execute(
            "SELECT size, qty, location, name FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)
        ).fetchall()
        price = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if not rows:
        return {"found": False, "error": f"No inventory rows for SKU {sku}."}
    return {
        "found": True,
        "sku": sku,
        "name": rows[0]["name"],
        "sizes": [{"size": r["size"], "qty": r["qty"], "location": r["location"]} for r in rows],
        "total_units": sum(r["qty"] for r in rows),
        "unit_cost": price["unit_cost"] if price else None,
        "list_price": price["list_price"] if price else None,
    }


@mcp.tool
def get_vendor_invoice(invoice_id: int) -> dict:
    """Look up one vendor invoice with the vendor behind it: amount, due date, status, and lead time.

    Reads the invoices, vendors, and desk tables. Reports whether the invoice is unpaid and how many
    days overdue it is as of the shop's date. A vendor will not ship new product while it has an
    open unpaid invoice.
    """
    with _db() as conn:
        row = conn.execute(
            """SELECT i.id AS invoice_id, i.amount, i.due_date, i.status, i.description,
                      v.id AS vendor_id, v.name AS vendor_name, v.specialty, v.lead_days
               FROM invoices i JOIN vendors v ON v.id = i.vendor_id
               WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        if row is None:
            return {"found": False, "error": f"No invoice with id {invoice_id}."}
        today = _shop_today(conn)
        pending = _open_request_for(conn, "invoice", invoice_id)

    result = {"found": True, **dict(row), "shop_date_today": today}
    days_past_due = _days_between(row["due_date"], today)
    result["is_unpaid"] = row["status"] == "open"
    result["days_overdue"] = max(days_past_due, 0)
    result["is_overdue"] = result["is_unpaid"] and days_past_due > 0
    result["pending_payment_request_id"] = pending["id"] if pending else None
    return result


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty, lead time in days, and any open unpaid invoices.

    Reads the vendors and invoices tables. A vendor with an open unpaid invoice will not ship new
    product, so can_ship_new_product is false until that invoice is paid.
    """
    with _db() as conn:
        vendors = conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
        open_invoices = conn.execute(
            "SELECT id, vendor_id, amount, due_date FROM invoices WHERE status = 'open'"
        ).fetchall()
    out = []
    for v in vendors:
        mine = [dict(i) for i in open_invoices if i["vendor_id"] == v["id"]]
        out.append({
            **dict(v),
            "open_unpaid_invoices": [{k: i[k] for k in ("id", "amount", "due_date")} for i in mine],
            "can_ship_new_product": not mine,
        })
    return {"vendors": out}


@mcp.tool
def get_lease_rent_due(lease_id: int) -> dict:
    """Look up one shop lease: space, landlord, monthly rent, and next due date.

    Reads the leases and desk tables. Reports how many days until rent is due as of the shop's date
    (negative means it is already late), so a rent notice can be checked against the real lease.
    """
    with _db() as conn:
        row = conn.execute(
            """SELECT id AS lease_id, space_name, landlord, monthly_rent, next_due, notes
               FROM leases WHERE id = ?""",
            (lease_id,),
        ).fetchone()
        if row is None:
            return {"found": False, "error": f"No lease with id {lease_id}."}
        today = _shop_today(conn)
        pending = _open_request_for(conn, "rent", lease_id)

    result = {"found": True, **dict(row), "shop_date_today": today}
    result["days_until_due"] = _days_between(today, row["next_due"])
    result["pending_payment_request_id"] = pending["id"] if pending else None
    return result


@mcp.tool
def get_cash_balance() -> dict:
    """Show the checking balance, how much is already promised to pending payment requests, and what is left.

    Reads the cash_accounts table (and pending payment_requests). The shop has no incoming money,
    so this balance only goes down.
    """
    with _db() as conn:
        checking = _checking(conn)
        pending = _pending_total(conn)
    return {
        "account": checking["name"],
        "balance": checking["balance"],
        "as_of": checking["date"],
        "pending_requests_total": pending,
        "available_after_pending": round(checking["balance"] - pending, 2),
    }


@mcp.tool
def list_payment_requests(status: str = "all") -> dict:
    """List payment and purchase-order requests, newest last. status: pending, approved, declined, or all.

    Reads the payment_requests table (created when the first request is made).
    """
    with _db() as conn:
        if not _has_requests_table(conn):
            return {"requests": []}
        if status == "all":
            rows = conn.execute("SELECT * FROM payment_requests ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM payment_requests WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
    return {"requests": [dict(r) for r in rows]}


# ---------------------------------------------------------------- agent requests (no cash moves)


@mcp.tool
def request_invoice_payment(invoice_id: int, ticket_id: int, reason: str, requested_by: str) -> dict:
    """Prepare payment of one open vendor invoice for human approval. The amount comes from the invoice.

    Reads invoices, vendors, cash_accounts; writes a pending row to payment_requests. No cash moves.
    Refused if the invoice isn't open, already has a pending request, or cash can't cover it.
    """
    with _db(write=True) as conn:
        inv = conn.execute(
            """SELECT i.id, i.amount, i.status, i.description, v.name AS vendor
               FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        if inv is None:
            return {"created": False, "refused": f"No invoice with id {invoice_id}."}
        if inv["status"] != "open":
            return {"created": False, "refused": f"Invoice {invoice_id} is '{inv['status']}', not open."}
        if (dup := _open_request_for(conn, "invoice", invoice_id)) is not None:
            return {"created": False, "refused": f"Request {dup['id']} for this invoice is already pending."}
        return _file_request(
            conn, kind="invoice", ref_id=invoice_id, payee=inv["vendor"], amount=inv["amount"],
            reason=reason, requested_by=requested_by, ticket_id=ticket_id,
        )


@mcp.tool
def request_rent_payment(lease_id: int, ticket_id: int, reason: str, requested_by: str) -> dict:
    """Prepare this month's rent for one lease for human approval. The amount comes from the lease.

    Reads leases, cash_accounts; writes a pending row to payment_requests. No cash moves.
    Refused if rent for this lease already has a pending request or cash can't cover it.
    """
    with _db(write=True) as conn:
        lease = conn.execute(
            "SELECT id, landlord, monthly_rent, next_due, space_name FROM leases WHERE id = ?", (lease_id,)
        ).fetchone()
        if lease is None:
            return {"created": False, "refused": f"No lease with id {lease_id}."}
        if (dup := _open_request_for(conn, "rent", lease_id)) is not None:
            return {"created": False, "refused": f"Request {dup['id']} for this rent is already pending."}
        return _file_request(
            conn, kind="rent", ref_id=lease_id, payee=lease["landlord"], amount=lease["monthly_rent"],
            reason=f"{reason} (rent due {lease['next_due']}, {lease['space_name']})",
            requested_by=requested_by, ticket_id=ticket_id,
        )


@mcp.tool
def request_purchase_order(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int,
                           reason: str, requested_by: str) -> dict:
    """Prepare a restock purchase order for human approval. Cost = qty x the SKU's unit_cost.

    Reads vendors, invoices, pricing, inventory, cash_accounts; writes a pending row to
    payment_requests. No cash moves. Refused if the vendor has an open unpaid invoice (it won't
    ship), the SKU/size doesn't exist, qty isn't positive, or cash can't cover it.
    """
    with _db(write=True) as conn:
        vendor = conn.execute("SELECT id, name, lead_days FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"created": False, "refused": f"No vendor with id {vendor_id}."}
        if qty <= 0:
            return {"created": False, "refused": "Quantity must be at least 1."}
        blocking = conn.execute(
            "SELECT id, amount FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,)
        ).fetchall()
        if blocking:
            ids = ", ".join(str(b["id"]) for b in blocking)
            return {
                "created": False,
                "refused": f"{vendor['name']} has open unpaid invoice(s) {ids} and will not ship new "
                           "product until they are paid.",
            }
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"created": False, "refused": f"No inventory row for SKU {sku} size {size}."}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"created": False, "refused": f"No pricing row for SKU {sku}."}
        amount = round(qty * price["unit_cost"], 2)
        result = _file_request(
            conn, kind="purchase_order", ref_id=vendor_id, payee=vendor["name"], amount=amount,
            reason=reason, requested_by=requested_by, ticket_id=ticket_id, sku=sku, size=size, qty=qty,
        )
        if result.get("created"):
            result["unit_cost"] = price["unit_cost"]
            result["vendor_lead_days"] = vendor["lead_days"]
        return result


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str) -> dict:
    """Change a ticket's status and add a dated note. status: open, in_progress, waiting_on_approval, resolved.

    Writes the tickets table. The note is appended to the ticket's notes, so the requester's
    original message is kept.
    """
    if status not in TICKET_STATUSES:
        return {"updated": False, "error": f"status must be one of {', '.join(TICKET_STATUSES)}"}
    with _db(write=True) as conn:
        row = conn.execute("SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"updated": False, "error": f"No ticket with id {ticket_id}."}
        today = _shop_today(conn)
        notes = (row["notes"] or "") + f"\n[{today} -> {status}] {note}"
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes.strip(), ticket_id))
    return {"updated": True, "ticket_id": ticket_id, "old_status": row["status"], "new_status": status}


# ---------------------------------------------------------------- human-only (never given to agents)


@mcp.tool
def approve_payment(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Pay one pending request: add a payments row, lower checking, update the paid table.

    Writes payments, cash_accounts, payment_requests, and invoices (status -> paid) or leases
    (next_due -> one month later). Refused if checking can't cover it or approved_by is missing or
    is an agent's role name. Purchase orders take cash now; the goods arrive after the vendor's
    lead days and are not added to inventory here.
    """
    who = (approved_by or "").strip()
    if not who or who.lower() in AGENT_NAMES:
        return {"approved": False, "refused": "approved_by must be the name of the human approving."}
    with _db(write=True) as conn:
        if not _has_requests_table(conn):
            return {"approved": False, "refused": "There are no payment requests."}
        req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"approved": False, "refused": f"No payment request {request_id}."}
        if req["status"] != "pending":
            return {"approved": False, "refused": f"Request {request_id} is already {req['status']}."}
        checking = _checking(conn)
        if req["amount"] > checking["balance"]:
            return {
                "approved": False,
                "refused": "Not enough cash. The checking balance can never go negative.",
                "amount": req["amount"],
                "checking_balance": checking["balance"],
            }
        today = _shop_today(conn)
        new_balance = round(checking["balance"] - req["amount"], 2)
        # payments.ref_id: invoice id, lease id, or (purchase orders) the request id = PO number
        ref = request_id if req["kind"] == "purchase_order" else req["ref_id"]
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], ref, req["amount"], "checking", today, who),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'", (new_balance, today)
        )
        updated = {}
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
            updated = {"invoice_id": req["ref_id"], "invoice_status": "paid"}
        elif req["kind"] == "rent":
            due = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()["next_due"]
            nxt = _add_one_month(due)
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (nxt, req["ref_id"]))
            updated = {"lease_id": req["ref_id"], "rent_paid_for": due, "next_due": nxt}
        else:
            lead = conn.execute("SELECT lead_days FROM vendors WHERE id = ?", (req["ref_id"],)).fetchone()["lead_days"]
            updated = {
                "purchase_order": request_id,
                "expected_arrival": date.fromordinal(date.fromisoformat(today).toordinal() + lead).isoformat(),
            }
        conn.execute(
            """UPDATE payment_requests SET status = 'approved', decided_by = ?, decided_at = ?, payment_id = ?
               WHERE id = ?""",
            (who, _now(), cur.lastrowid, request_id),
        )
        still_pending = conn.execute(
            "SELECT COUNT(*) FROM payment_requests WHERE ticket_id = ? AND status = 'pending'", (req["ticket_id"],)
        ).fetchone()[0]
    return {
        "approved": True,
        "payment_id": cur.lastrowid,
        "kind": req["kind"],
        "payee": req["payee"],
        "amount": req["amount"],
        "approved_by": who,
        "paid_at": today,
        "checking_before": checking["balance"],
        "checking_after": new_balance,
        "updated": updated,
        "ticket_id": req["ticket_id"],
        "ticket_pending_requests_left": still_pending,
    }


@mcp.tool
def decline_payment(request_id: int, declined_by: str, reason: str) -> dict:
    """HUMAN ONLY. Decline one pending request. No cash moves.

    Writes the payment_requests table.
    """
    who = (declined_by or "").strip()
    if not who or who.lower() in AGENT_NAMES:
        return {"declined": False, "refused": "declined_by must be the name of the human declining."}
    with _db(write=True) as conn:
        if not _has_requests_table(conn):
            return {"declined": False, "refused": "There are no payment requests."}
        req = conn.execute("SELECT status FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"declined": False, "refused": f"No payment request {request_id}."}
        if req["status"] != "pending":
            return {"declined": False, "refused": f"Request {request_id} is already {req['status']}."}
        conn.execute(
            """UPDATE payment_requests SET status = 'declined', decided_by = ?, decided_at = ?, decision_note = ?
               WHERE id = ?""",
            (who, _now(), reason, request_id),
        )
    return {"declined": True, "request_id": request_id, "declined_by": who}


if __name__ == "__main__":
    mcp.run(show_banner=False)  # stdio transport; never print to stdout here
