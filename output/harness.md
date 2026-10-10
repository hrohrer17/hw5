# Campus Customs — Agent Harness

This file maps everything the Campus Customs agent team works with: the database tables, the MCP
tools, the five agents, the API routes, the dashboard, and the safety rules.

The agents read and update the **working copy**, `data/campus_customs_new.db`. The original,
`data/campus_customs.db`, stays untouched so the shop can be reset for a clean run.

---

## Database tables

`data/campus_customs.db` has 9 tables. Every field below is a real column from the database. Row counts
and statuses are for the original database, before any run.

### `desk` (1 row)
| Field | Meaning |
|---|---|
| `date_today` | The shop's "today" (`2026-08-31`) |
| `notes` | Free-text desk notes (currently empty) |

**Why it matters:** every agent judges "overdue", "due soon" and "in the past" against
`date_today`, never the real calendar date.

### `tickets` (3 rows, all `open`)
| Field | Meaning |
|---|---|
| `id` | Ticket number (101, 102, 103) |
| `type` | Kind of request: `customer_order`, `rent_notice`, `price_override` |
| `requester` | Who asked (a customer, the landlord, a student org) |
| `subject` | One-line title |
| `sku` | Product the ticket is about, if any |
| `size` | Product size, if any |
| `qty` | Units requested, if any |
| `lease_id` | Linked lease, if it is a rent ticket |
| `invoice_id` | Linked vendor invoice, if one is involved |
| `status` | `open` or resolved |
| `notes` | The requester's message |
| `created_at` | When the ticket came in |

**Why it matters:** this is the Boss's inbox. The ticket's `type` and filled-in link fields
(`sku`/`size`, `lease_id`, `invoice_id`) tell the Boss which specialists to send it to.

### `inventory` (10 rows)
| Field | Meaning |
|---|---|
| `sku` | Product code |
| `name` | Product name |
| `size` | S / M / L / XL, or OS (one size) |
| `qty` | Units on hand |
| `location` | Aisle in the shop |

**Why it matters:** the Inventory agent checks stock here by SKU and size to spot shortfalls
before anyone promises a customer an order.

### `pricing` (4 rows)
| Field | Meaning |
|---|---|
| `sku` | Product code |
| `unit_cost` | What the shop pays per unit |
| `list_price` | What the shop normally charges |

**Why it matters:** Accounting uses the gap between `unit_cost` and `list_price` to check
margins, for example to know how deep a discount can go before the shop loses money.

### `vendors` (3 rows)
| Field | Meaning |
|---|---|
| `id` | Vendor number |
| `name` | Vendor name |
| `specialty` | What they supply (apparel reprint, mugs and small goods, local courier) |
| `lead_days` | Days from order to delivery |

**Why it matters:** Inventory picks the right vendor to restock from here. `lead_days` is the
only source for how long a restock will take.

### `invoices` (1 row)
| Field | Meaning |
|---|---|
| `id` | Invoice number |
| `vendor_id` | Which vendor billed the shop (links to `vendors.id`) |
| `amount` | Amount owed |
| `due_date` | When it was due |
| `status` | `open` (unpaid) or paid |
| `description` | What the invoice was for |

**Why it matters:** Accounting watches unpaid bills here. A vendor with an open unpaid invoice
will not ship new product, so this table can block a restock.

### `leases` (1 row)
| Field | Meaning |
|---|---|
| `id` | Lease number |
| `space_name` | Which shop space |
| `landlord` | Who the rent is paid to |
| `monthly_rent` | Rent amount |
| `next_due` | Next rent due date |
| `notes` | Free-text lease notes (currently empty) |

**Why it matters:** the Facilities agent uses this to confirm a rent notice is real (right
landlord, right amount, right due date) before Accounting prepares any payment.

### `cash_accounts` (1 row)
| Field | Meaning |
|---|---|
| `name` | Account name (`checking`) |
| `balance` | Current balance |
| `date` | Date of that balance |

**Why it matters:** Accounting checks this before preparing any payment. A payment the balance
can't cover must be refused, because the balance can never go negative.

### `payments` (0 rows)
| Field | Meaning |
|---|---|
| `id` | Payment number |
| `kind` | What was paid (e.g. an invoice or rent) |
| `ref_id` | ID of the invoice or lease that was paid |
| `amount` | Amount paid |
| `account` | Which cash account it came from |
| `paid_at` | When it was paid |
| `approved_by` | The human who approved it |

**Why it matters:** this is the record of money going out. Each approved payment gets a row here,
with the approving human's name, so there is an audit trail.

---

### `payment_requests` (added by the MCP server, not in the original database)
| Field | Meaning |
|---|---|
| `id` | Request number (for purchase orders, this is the PO number) |
| `kind` | `invoice`, `rent`, or `purchase_order` |
| `ref_id` | The invoice id, lease id, or (for purchase orders) vendor id |
| `payee` | Who would be paid |
| `amount` | Taken from the database (invoice amount, monthly rent, or qty × unit cost), never typed by an agent |
| `sku`, `size`, `qty` | Purchase orders only |
| `ticket_id` | The ticket the request is for |
| `reason` | The agent's one-sentence justification |
| `requested_by` | The agent that filed it (stamped by the backend, so an agent can't file under another name) |
| `status` | `pending`, `approved`, or `declined` |
| `created_at`, `decided_by`, `decided_at`, `decision_note`, `payment_id` | When it was filed, who decided, and the `payments` row it became |

**Why it matters:** this is the hand-off point between agents and humans. Agents can only add
`pending` rows here. Cash moves only when a human approves a row. It's created on first use, so
resetting the working copy from the original removes it.

---

## MCP tools — the first three (Problem 3)

The `campus-customs` MCP server (`mcp_server/server.py`, built with FastMCP) reads
`data/campus_customs_new.db`. These first three tools are read-only and return only what is in the
database. Day counts use `desk.date_today`.

| Tool | Table(s) it reads | Ticket it unlocks | Why it's the right tool for that ticket |
|---|---|---|---|
| `check_stock_and_pricing(sku, size)` | `inventory`, `pricing` | **103** (Yale AI Club, 20 × CC-HOOD-NAVY size M, asking for a bulk discount) | In one call it shows only 8 size-M navy hoodies on the shelf against the 20 requested, and a $22 unit cost against the $58 list price, so the team knows both the shortfall and how deep a discount can go before the order loses money. |
| `get_vendor_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | **101** (Tauhid Zaman, 1 × CC-TEE-WHITE size S; the S shelf has 0) | Ticket 101 links to invoice 501: Bulldog Print Co's $840 "Rush reprint CC-TEE-WHITE S", still open and 3 days overdue as of 2026-08-31. Since a vendor won't ship while an invoice is unpaid, this tool shows what has to be paid before the S tee can be reprinted (and Bulldog's 5-day lead time). |
| `get_lease_rent_due(lease_id)` | `leases`, `desk` | **102** (Elm City Properties emails that rent is due in 2 days) | Ticket 102 links to lease 1, and the tool confirms the notice is real: the Chapel Street shop, landlord Elm City Properties, $2,400 rent due 2026-09-02, 2 days after the shop's date. Facilities can verify it before Accounting prepares a payment. |

---

## MCP tools — full list (Problem 5)

All tools are on the one `campus-customs` server and work on `data/campus_customs_new.db`.

| Tool | Table(s) it uses | Reads / writes | Used by |
|---|---|---|---|
| `list_tickets()` | `tickets`, `desk` (every ticket with status, notes, and links) | read | Boss, and the API's `GET /tickets` |
| `get_ticket(ticket_id)` | `tickets`, `desk` | read | all five |
| `check_stock_and_pricing(sku, size)` | `inventory`, `pricing` | read | Inventory, Accounting, Customer Service |
| `list_stock_for_sku(sku)` | `inventory`, `pricing` | read | Inventory, Customer Service |
| `get_vendor_invoice(invoice_id)` | `invoices`, `vendors`, `desk` (+ `payment_requests`) | read | Inventory, Accounting |
| `list_vendors()` | `vendors`, `invoices` | read | Inventory, Accounting, Customer Service |
| `get_lease_rent_due(lease_id)` | `leases`, `desk` (+ `payment_requests`) | read | Accounting, Facilities |
| `get_cash_balance()` | `cash_accounts` (+ `payment_requests`) | read | Boss, Accounting, Facilities |
| `list_payment_requests(status)` | `payment_requests` | read | Boss, Accounting, Facilities, Customer Service |
| `request_invoice_payment(invoice_id, ticket_id, reason, requested_by)` | reads `invoices`, `vendors`, `cash_accounts`; writes `payment_requests` | write (pending only) | Accounting |
| `request_rent_payment(lease_id, ticket_id, reason, requested_by)` | reads `leases`, `cash_accounts`; writes `payment_requests` | write (pending only) | Accounting |
| `request_purchase_order(vendor_id, sku, size, qty, ticket_id, reason, requested_by)` | reads `vendors`, `invoices`, `inventory`, `pricing`, `cash_accounts`; writes `payment_requests` | write (pending only) | Accounting |
| `update_ticket_status(ticket_id, status, note)` | `tickets` | write | Boss |
| `approve_payment(request_id, approved_by)` | writes `payments`, `cash_accounts`, `payment_requests`, and `invoices` (→ paid) or `leases` (→ next due date) | write (moves cash) | **human only** |
| `decline_payment(request_id, declined_by, reason)` | `payment_requests` | write | **human only** |

---

## The agent team (Problem 5)

Five PydanticAI agents live in `backend/team.py`, with one prompt file each in `backend/prompts/`
and the data types in `backend/models.py`. **Every agent runs on `gpt-6-luna` through Portkey**
(`backend/config.py`; the model name is hard-coded with no override). They get shop facts only
from the MCP server.

**Full connectivity:** every agent has a `delegate(to_agent, task)` tool that can hand work to any
other agent, the Boss included. A teammate answers using its own tools and replies to whoever
asked. Hand-offs can chain (Boss → Facilities → Accounting) up to 3 deep.

| Agent | Prompt | What it does | MCP tools it may call |
|---|---|---|---|
| **Boss** | `prompts/boss.md` | Reads each ticket, decides who works on it, makes the final call, sets the ticket status (**resolved means the team made its decision**; outside steps become follow-ups; `waiting_on_approval` while a payment awaits a human), returns the structured outcome (`TicketOutcome`) | `list_tickets`, `get_ticket`, `get_cash_balance`, `list_payment_requests`, `update_ticket_status` |
| **Inventory** | `prompts/inventory.md` | Checks stock by SKU and size, spots shortfalls, picks the vendor who can restock, works out lead time and whether an unpaid invoice blocks shipping | `get_ticket`, `check_stock_and_pricing`, `list_stock_for_sku`, `list_vendors`, `get_vendor_invoice` |
| **Accounting** | `prompts/accounting.md` | Watches cash and invoices, checks margins on discounts, prepares invoice, rent, and purchase-order payments for human approval | `get_ticket`, `get_cash_balance`, `get_vendor_invoice`, `get_lease_rent_due`, `check_stock_and_pricing`, `list_vendors`, `list_payment_requests`, `request_invoice_payment`, `request_rent_payment`, `request_purchase_order` |
| **Facilities** | `prompts/facilities.md` | Verifies rent and space notices against the lease (landlord, amount, due date), tracks rent timing, hands verified rent to Accounting | `get_ticket`, `get_lease_rent_due`, `get_cash_balance`, `list_payment_requests` |
| **Customer Service** | `prompts/customer_service.md` | Writes draft messages to customers, student groups, and the landlord using only verified facts; never sends anything | `get_ticket`, `check_stock_and_pricing`, `list_stock_for_sku`, `list_vendors`, `list_payment_requests` |

**No agent** can call `approve_payment` or `decline_payment`; those are for a human only.

---

## Audit trail

Every agent-loop step is appended to `output/audit_trail.json` (`backend/audit.py`). It's one
JSON array that is only ever added to, never wiped. Each entry has a timestamp, `run_id`,
`ticket_id`, `agent`, hand-off `depth`, `step`, and `event`, plus the details:

| Event | What's recorded |
|---|---|
| `run_start` / `run_finish` | Model, the cost limits in force, total tokens and requests used, final status, any error |
| `agent_start` / `agent_finish` | The task the agent was given, and its final answer |
| `model_request` | What went to the model that step: the prompt, or the results of the tools it called |
| `model_response` | What the model decided: its text, the tool calls with arguments, and input/output tokens. `model` is always `gpt-6-luna`; `provider_model` is Portkey's deployment name for it (`gpt-6-luna-global`) |
| `delegation` / `delegation_reply` / `delegation_refused` | Who handed what to whom, the reply, or why a hand-off was blocked |

---

## API routes (Problem 7)

FastAPI app in `backend/main.py`. Start it from `backend/` with
`uvicorn main:app --reload --port 8000`; it serves at http://localhost:8000. Shop data is read and
changed through the same campus-customs MCP server the agents use. CORS allows the Vite dashboard
origin (`http://localhost:5173`) to call these routes from the browser.

- `GET /tickets`: the three tickets with their status (`open` / `in_progress` / `waiting_on_approval` / `resolved`), a simple `state` (open or resolved), any payments waiting on a human, and the last run's outcome.
- `POST /tickets/{ticket_id}/run`: runs the agent team on that ticket in the background and returns a `run_id` right away (`?wait=true` waits and returns the full result). One run at a time.
- `GET /events`: recent agent events from `output/audit_trail.json` (what each agent said, which tools it called, hand-offs, approvals) with a one-line summary each. Filter with `?after=<seq>`, `?ticket_id=`, `?run_id=` so the board can refresh.
- `POST /payments/{request_id}/approve` (body `{"approved_by": "<human name>"}`): a human approves a payment or purchase the agents prepared. **The only route that changes cash.** It records the payment, lowers checking, marks the invoice paid or moves the rent due date, and resolves the ticket if nothing else is pending.
- `GET /cash`: the current checking balance from `cash_accounts`, plus what's promised to pending requests.
- `POST /reset`: copies the original `data/campus_customs.db` over `data/campus_customs_new.db` for a fresh run (refused while a ticket is running). The audit trail is kept and gets a reset marker.

---

## Dashboard (Problem 8)

React + Vite + TypeScript in `frontend/`. Start it with `npm run dev` (http://localhost:5173); it
calls the API at http://localhost:8000 (`VITE_API_URL` overrides that). Full design notes are in
`output/design.md`.

| Part of the board | What it shows | API it uses |
|---|---|---|
| Top bar | Shop date (`desk.date_today`), "Approving as" name, checking balance with a meter showing money promised to pending requests | `GET /tickets`, `GET /cash` |
| Ticket queue | The 3 tickets: type, requester, item, status pill (Open / Agents working / Needs your approval / In progress / Resolved), a check seal and progress bar for resolved ones | `GET /tickets` |
| Team floor | Five agent desks (own color and icon) with live status: reading, using a tool, waiting on a teammate, done, or "not needed on this ticket"; tool-call counts | `GET /events` |
| Live conversation | Speech bubbles, hand-off cards (who → whom, with the task), tool calls with arguments and expandable results, replies, the Boss's final call, run cost (model calls, tokens), human approvals | `GET /events?after=` (polled every 0.9 s during a run) |
| Run button | Starts the team on the selected ticket | `POST /tickets/{id}/run` |
| Needs your approval | Each pending payment: amount, payee, reason, preparing agent, **Approve & pay** | `POST /payments/{id}/approve` |
| What each agent did | One line per agent, including "Didn't do anything on this ticket" | `GET /events` (the run's outcome) |
| Outcome, draft reply, cash-out ledger, reset | The Boss's outcome (plus any approval since), the unsent customer draft, payments since reset with the starting and current balance, and the reset button | `GET /events`, `POST /reset` |

---

## Safety

**Guardrails for real customers and real money**

- **A human approves every dollar.** Agents can only file *pending* requests. Paying is a separate
  `approve_payment` tool that no agent is given, and it rejects an approver name that is an agent
  role ("Accounting", "Boss", ...). The approver's name is saved in `payments.approved_by`.
- **No negative cash.** Request and approval both check the checking balance; a request also counts
  money already promised to pending requests. If the money isn't there, the tool refuses.
- **Amounts come from the database, not the model.** Invoice amount, monthly rent, and qty ×
  unit cost are looked up by the tool, so an agent can't mistype or inflate a payment.
- **Duplicate and blocked payments are refused:** a second request for the same invoice or rent,
  an invoice that isn't open, and a purchase order to a vendor with an open unpaid invoice.
- **Least privilege.** Each agent sees only the MCP tools its job needs (table above), and the
  backend stamps `requested_by` with the real agent name.
- **One source of truth.** Shop facts come only from the MCP server over the working database. No
  agent touches the database directly, and the original database is read-only.
- **No outside contact.** Nobody emails customers or calls vendors or the landlord. Customer Service
  writes drafts that a human reviews on the dashboard.
- **Never invent data.** Tools return `found: false` instead of guessing, and the prompts require
  every number to come from a tool.
- **Private stays private.** Customer drafts never mention cash, margins, costs, or unpaid bills.
- **Full audit trail** of every step, every tool call and result, every hand-off, and every token
  count, so a human can trace any decision.

- **Guardrails on the dashboard too:** you can't approve without typing your name ("Approving as");
  each request shows its amount, payee, the preparing agent, and the reason before you pay. Drafts
  are labeled "Draft · not sent". Reset asks for confirmation and is blocked while a ticket runs.
- **One ticket runs at a time,** so two runs can't both count the same cash.
- **The MCP server process gets no API keys:** it starts with only `PATH`/`HOME` (and a test DB
  path if set), and it exits when its run or the API ends (`keep_alive=False`).
- **The original database is read-only** (`chmod 444`) and is only ever copied *from* on reset.

**Limits that keep token use in check** (`backend/config.py`)

| Limit | Value | Why |
|---|---|---|
| Model | `gpt-6-luna` only, no override | The cheaper model; one place to change it |
| Model calls per ticket run (all agents together) | 40 | Shared usage counter; the run stops cleanly if hit |
| Tool calls per ticket run | 60 | Stops a tool-call loop |
| Total tokens per ticket run | 300,000 | Hard spending cap per ticket |
| Hand-off depth | 3 | Boss → A → B → C at most |
| Hand-offs per ticket | 10 | Stops a team that keeps passing work around |
| No hand-off back into the current chain | — | Prevents A → B → A loops |
| Max output per model reply | 6,000 tokens | Stops runaway answers |
| Tool results clipped in the audit trail | 2,000 chars | Keeps the trail readable |
| Prompts | "only call the teammates you need", "one task per teammate", "report back instead of re-delegating" | Cuts repeat hand-offs. In a test before these lines, the Boss asked Inventory the same question twice (ticket 101: 25 model calls, 64k tokens) |

---

## Results of the full run (Problem 9)

The working database was reset (checking **$3,400.00**), then tickets 101, 102 and 103 were run
on the dashboard, with payments approved there by a human (recorded as "AI Foundation Student HR").

| Ticket | Final status | Cash change | Why |
|---|---|---|---|
| 101 Bulldog tee | resolved | −$840.00 | Paid overdue invoice 501 to Bulldog Print Co so it will ship the size S restock |
| 102 Rent due | resolved | −$2,400.00 | Paid lease 1 rent to Elm City Properties after Facilities verified the notice |
| 103 Bulk hoodie discount | resolved (6th attempt) | $0.00 | Quoted $53/hoodie (above the $22 cost) and offered the 8 in stock; the 12-unit restock ($264) exceeds the $160 left, so nothing was bought and the restock became a follow-up. Attempts 1–5 ended in progress at that cash limit; before attempt 6 the Boss's rule became "resolved means the team made its decision" |

Ending checking balance **$160.00**, which matches `cash_accounts`. Details are in
`output/desk_tickets.html` (Actual and Cash tabs), `output/resolved_tickets.json`,
`output/resolved_board.html`, and every step is in `output/audit_trail.json`.
