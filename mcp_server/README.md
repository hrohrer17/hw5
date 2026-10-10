# campus-customs MCP server

**What it's for:** it gives the Campus Customs agent team (Boss, Inventory, Accounting, Facilities,
Customer Service) one shared, trusted way to look up and change shop data. The agents ask the
server instead of guessing, so every number they use comes from the database, and every change
goes through rules enforced in code.

**Database:** `data/campus_customs_new.db`, the working copy. The original
`data/campus_customs.db` is never touched, so it can be copied back over the working copy to
reset the shop. "Today" for the shop is `desk.date_today` (2026-08-31), not the real date. Set
`CAMPUS_DB_PATH` to point the server at a different copy (used for test runs).

**Built with:** FastMCP (Python), stdio transport. Entry point: `mcp_server/server.py`.

## Tools (15)

**Look-ups (read-only)**

| Tool | Reads | What it returns |
|---|---|---|
| `list_tickets()` | `tickets`, `desk` | Every ticket's id, type, requester, subject, and status |
| `get_ticket(ticket_id)` | `tickets`, `desk` | One ticket in full, including its links (sku/size/qty, lease_id, invoice_id) |
| `check_stock_and_pricing(sku, size)` | `inventory`, `pricing` | Units on hand, aisle, unit cost, list price, margin per unit. Example: CC-HOOD-NAVY M has 8 on hand, $22 cost, $58 list |
| `list_stock_for_sku(sku)` | `inventory`, `pricing` | Stock for every size of one product. Example: CC-HOOD-NAVY is S 4, M 8, L 14, XL 6 |
| `get_vendor_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | Invoice amount, due date, status, vendor, lead days, days overdue. Example: invoice 501 is $840 to Bulldog Print Co, 3 days overdue |
| `list_vendors()` | `vendors`, `invoices` | Each vendor's specialty, lead days, open unpaid invoices, and whether it will ship new product |
| `get_lease_rent_due(lease_id)` | `leases`, `desk` | Space, landlord, monthly rent, next due date, days until due. Example: lease 1 is Chapel Street, $2,400 due 2026-09-02 |
| `get_cash_balance()` | `cash_accounts` | Checking balance, the total already promised to pending requests, and what's left |
| `list_payment_requests(status)` | `payment_requests` | Pending, approved, or declined payment requests |

**Agent requests (write a *pending* request; no cash moves)**

| Tool | What it does | Refuses when |
|---|---|---|
| `request_invoice_payment(invoice_id, ticket_id, reason, requested_by)` | Queues payment of an open vendor invoice, at the invoice amount | Invoice not open, already pending, or not enough cash |
| `request_rent_payment(lease_id, ticket_id, reason, requested_by)` | Queues the next rent on a lease, at the monthly rent | Already pending, or not enough cash |
| `request_purchase_order(vendor_id, sku, size, qty, ticket_id, reason, requested_by)` | Queues a restock at qty × unit cost | Vendor has an open unpaid invoice, unknown SKU/size, qty < 1, or not enough cash |
| `update_ticket_status(ticket_id, status, note)` | Sets `open` / `in_progress` / `waiting_on_approval` / `resolved` and appends a dated note | Unknown status or ticket |

**Human only (not given to any agent)**

| Tool | What it does |
|---|---|
| `approve_payment(request_id, approved_by)` | Pays a pending request: adds a `payments` row, lowers checking, and marks the invoice paid or moves the lease's next due date one month. Refuses if checking would go negative or the approver is an agent role name |
| `decline_payment(request_id, declined_by, reason)` | Declines a pending request; no cash moves |

Pending requests live in a `payment_requests` table that the server creates on first use. It
isn't in the original database, so a reset removes it.

If a SKU, size, invoice, lease, or ticket isn't in the database, the tool returns `found: false`
(or `created: false` with a reason). It never fills in made-up values.
