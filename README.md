# Campus Customs: Multi-Agent Operations (MGT409 Homework 5)

Five AI agents (**Boss, Inventory, Accounting, Facilities, Customer Service**) run the back office of
Campus Customs, a small Yale apparel shop. They work the shop's tickets: a customer order, a rent
notice, and a bulk-discount request. A human watches them on a React dashboard and is the only one
who can approve spending money.

Three pieces talk to each other:

| Piece | Folder | What it does |
|---|---|---|
| MCP server | `mcp_server/` | FastMCP server over `data/campus_customs_new.db`: 15 tools for tickets, stock, pricing, vendors, invoices, leases, cash, payment requests, and human-only approval |
| Agent team + API | `backend/` | Five PydanticAI agents on **gpt-6-luna** (via Portkey) that can delegate to each other, plus a FastAPI app the board calls |
| Dashboard | `frontend/` | React + Vite + TypeScript board: pick a ticket, watch the agents work live, approve payments, watch checking drop |

## Setup (once)

You need Python 3.12+, Node 20+, and a Portkey API key.

```bash
# from this hw5/ folder
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                   # then put your PORTKEY_API_KEY in .env (never commit it)

cd frontend && npm install && cd ..
```

## 1. Copy the original database to the working copy (for a clean run)

`data/campus_customs.db` is the **original** and is never changed. `data/campus_customs_new.db` is the
**working copy** that the MCP server, agents, and backend read and update. To start clean, copy the
original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Do this while the backend is stopped, or use the Reset button / route in step 5 while it's running.
The committed working copy holds the state after our full run (all three tickets resolved, checking
$160), so copy the original first if you want to watch the run from the start.

## 2. Start the MCP server

The backend starts its own copy of the MCP server automatically (over stdio) when it runs, so for the
app you don't need a separate terminal. To run the server on its own, for example for a vibe coder:

```bash
python mcp_server/server.py
```

It's a stdio server, so it sits waiting for an MCP client to talk to it over standard input/output;
that's normal. To use the tools from Claude Code, open Claude Code in this `hw5/` folder and approve
**campus-customs** when asked. `.mcp.json` works as is, with no paths to edit: it runs
`mcp_server/server.py` with this folder's `.venv/bin/python` (from Setup), or `python3` if there's no
`.venv`. `mcp_server/README.md` lists every tool.

## 3. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API runs at http://localhost:8000 (interactive docs at http://localhost:8000/docs). Routes:
`GET /tickets`, `POST /tickets/{id}/run`, `GET /events`, `POST /payments/{id}/approve`, `GET /cash`,
`POST /reset`. Agent steps are appended to `output/audit_trail.json`.

## 4. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. Type your name in **Approving as**, pick a ticket, press **Run the team**,
and watch the agents. When the team prepares a payment, it shows under **Needs your approval**.
**Approve & pay** is the only thing that moves cash.

## 5. Reset the database before a full three-ticket run

Before running tickets 101, 102 and 103 from scratch, reset the working copy to the original values.
Any one of these works:

- On the board: **Reset the shop for a fresh run** (bottom of the right column), or
- With the backend running: `curl -X POST http://localhost:8000/reset`, or
- With the backend stopped: the `cp` command in step 1.

After a reset, checking is back to **$3,400.00** and all three tickets are open. The audit trail is
kept (it's append-only) and gets a reset marker. Then run 101 → approve → 102 → approve → 103.

## Results and write-ups (`output/`)

| File | What's in it |
|---|---|
| `harness.md` | Tables, MCP tools, the five agents, API routes, dashboard, safety rules, and results |
| `mcp_smoke.json` | Our test of the first three MCP tools from the vibe coder |
| `desk_tickets.html` | Open by double-clicking: Expected vs Actual for each ticket, the Cash ledger, and the Reflection |
| `design.md` | Why the dashboard looks and works the way it does |
| `resolved_tickets.json` | Each ticket's final status, outcome, each agent's contribution, and human approvals |
| `resolved_board.html` | Open by double-clicking: screenshots of the board for tickets 101, 102 and 103 |
| `audit_trail.json` | Every agent-loop step of the real runs |
| `github_url.txt` | This repo's URL |

Our full run on the reset database: checking **$3,400.00 → $2,560.00** (101, vendor invoice 501, $840) **→
$160.00** (102, rent, $2,400); 103 resolved with a $53/hoodie quote and no spending. The ending balance
matches `cash_accounts`.

## Safety, briefly

Agents can only *request* payments. A human approves on the board, and the approval tool refuses
anything that would push checking below $0. Amounts come from the database, not the model. Nobody
emails customers or contacts vendors; Customer Service writes drafts only. Every agent uses only
gpt-6-luna, with per-ticket caps on model calls, tool calls, tokens, and hand-offs. Details are in
`output/harness.md`.
