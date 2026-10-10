# Campus Customs Desk: dashboard design

The board in `frontend/` (React + Vite + TypeScript) is where a human manager sits while five AI
agents work the shop's tickets. The goal: at any moment, you can see **what's on the desk, who's
working on it, what they're saying, and how much money is at stake**, and the one thing only you
can do (approving a payment) is impossible to miss.

Start it with `npm run dev` in `frontend/` (http://localhost:5173). It talks to the FastAPI backend
at http://localhost:8000.

---

## Layout: three columns, read left to right like a real desk

```
┌──────────────── garnet top bar: crest · shop date · "Approving as" · CASH METER ────────────────┐
│ TICKET QUEUE        │  TEAM FLOOR: five agent desks with live status          │ NEEDS YOUR APPROVAL │
│ #101 Bulldog tee    │──────────────────────────────────────────────────────────│ WHAT EACH AGENT DID │
│ #102 Rent due       │  LIVE CONVERSATION                                       │ OUTCOME             │
│ #103 Hoodie deal    │  Boss → Facilities hand-off, tool calls, replies, final  │ DRAFT REPLY         │
│ progress: 1/3 done  │  call, "PAID" when you approve                           │ CASH OUT LEDGER     │
└─────────────────────┴──────────────────────────────────────────────────────────┴─────────────────────┘
```

- **Left: the inbox.** The three tickets as cards with an icon per type (shopping bag for the
  order, building for the rent notice, price tag for the discount request), who sent each, what it's
  about, and a status pill. A thin progress bar on top fills as tickets get resolved.
- **Center: the work.** The five agents sit across the top like desks in an office. Below them, the
  selected ticket's conversation streams in while the team works. The big **Run the team** button
  sits next to the ticket title, right where you're looking.
- **Right: decisions and results.** Anything waiting on you goes at the top, then the per-agent
  summary, the outcome, the customer draft, and a cash ledger.
- **Why:** this follows the order a manager thinks in: *what came in → who's handling it → what do I
  need to decide.* Panels on the left and right stay put while the conversation scrolls, so the
  queue and the approval button never scroll away. On a smaller screen the right column drops below
  and the agent desks wrap onto two rows.

## How the agents read differently

Each agent has its own **color and icon**, used everywhere it appears: its desk, its avatar in the
conversation, its speech bubbles, its tool chips, and its line in the summary.

| Agent | Color | Icon | Why |
|---|---|---|---|
| Boss | Garnet | Crown | The house color goes to the one who makes the call |
| Inventory | Teal | Box | Stock and shelves |
| Accounting | Gold | Receipt | Money |
| Facilities | Forest green | Building | The shop space |
| Customer Service | Plum | Speech bubble | Talking to people |

The accents are muted so they sit comfortably next to the garnet-and-white theme instead of turning
the page into a rainbow. You can tell who's talking from the edge of your eye, without reading names.

**Live status on each desk.** A dot and a short line say what each agent is doing right now:
*Reading the task*, *Using get_lease_rent_due*, *Waiting on Accounting*, *Done*. Active agents get
a soft pulsing ring and a tinted card; waiting agents turn amber. A small counter shows each agent's
tool calls. Agents the Boss didn't need fade out after the run with "Not needed on this ticket".
That makes the efficiency point visible: on the rent ticket, Inventory sits it out.

**The conversation reads like a team chat, not a log file:**
- **Speech bubbles** for what an agent says, in its tint.
- **Hand-off cards** ("Facilities → Accounting") with the full task text, so you can see exactly what
  was asked.
- **Tool chips** in monospace with the arguments in plain words (`get_lease_rent_due · lease id 1`),
  and a collapsible "↳ returned" line under each if you want the raw data.
- **Replies** indented under the hand-off they answer, so nested delegation reads as a thread.
- **The Boss's final call** gets its own garnet card.
- A three-dot "typing" indicator while the team is still working.
- Dividers mark the start and end of a run. The end divider shows the model calls and tokens used,
  so cost is never hidden.

## How resolved tickets show up

- The status pill moves through **Open → Agents working → Needs your approval → Resolved**, color-coded
  (grey, pulsing garnet, amber, green).
- A resolved ticket gets a **garnet wax-seal check mark** that pops onto its card, the queue's
  progress bar fills, and the counter reads "1/3 resolved". The Run button changes to "Resolved ✓".
- Every agent's line in **What each agent did** is filled in: the Boss's write-up of each agent's
  part, or **"Didn't do anything on this ticket"** for agents that weren't called.
- The Outcome card shows what the Boss concluded at the end of the run. If a human approved
  something afterward, a green **"Since then: … approved … Ticket resolved."** line is added, so the
  record stays honest about the order of events.

## How cash shows up

- **The checking balance is the biggest number on the page,** in a white card on the garnet bar. It
  never scrolls away.
- **A cash meter under it** shows the balance against the starting balance. Money the team has
  *requested* but you haven't approved shows as a **hatched "promised" segment**, with a note like
  "$2,400 promised · $1,000 free". You see what a payment would do before you approve it.
- **When you approve,** the number **counts down** to the new balance (for example $3,400 → $1,000),
  the bar shrinks, the card glows for a moment, a **"PAID" rubber stamp** lands on the request, and a
  green line appears in the conversation: "Test Approver approved $2,400.00 to Elm City
  Properties. Checking $3,400 → $1,000".
- **A "Cash out since reset" ledger** lists each payment with its ticket number, payee, and amount,
  from the starting balance down to "Now". It's the same itemized view the Cash tab will need.

## Built-in guardrails you can see

- **"Approving as"** sits in the top bar. You can't approve without typing your name, and that name
  is saved on the payment record. Agents only *prepare* payments; the footer of the queue says so.
- The approval card shows the amount, payee, request number, which agent prepared it, and the
  team's one-sentence reason.
- The customer draft is labeled **"Draft · not sent"**, shown on lined notepaper, with a Copy button.
  Nothing is ever emailed.
- **"Shop date: Mon, Aug 31, 2026"** sits in the header, because agents judge "overdue" against the
  shop's date, not today's. Hovering explains that.
- Only one ticket runs at a time (the button says "Another ticket is running"), and **Reset** asks
  for confirmation and is disabled during a run.
- If the backend is down, a banner says so and gives the command to start it.

## The creative touches, and why they matter

- **A collegiate crest and serif wordmark** (Georgia) for "Campus Customs": it feels like a Yale
  shop, not a generic admin template. The serif also carries through to ticket titles and the
  draft letter.
- **Warm paper background, white cards, soft shadows:** calmer than a stark white screen for
  something you'd sit at all day.
- **The rubber stamp, the wax seal, the counting balance:** small physical metaphors that make
  approving money feel deliberate and satisfying, and make "resolved" feel like something
  finished.
- **Motion with a purpose only:** pulses mean "working", amber means "waiting", the stamp means
  "paid". Everything turns off for people who set "reduce motion" in their system settings.
- **Cost on the page:** model calls and tokens per run sit next to the per-agent summary, so the
  people paying for the agents can see what each ticket cost.

## Why these choices

The board has to answer three questions at a glance: *Is anything waiting on me? Is the team doing
the right thing? Where is the money?* The approval card is the most prominent thing on the right,
the agents' identities make the conversation scannable, and cash is always visible with its
"promised" part shown before it's spent. The polish makes it a desk someone would want to sit at,
and every flourish also tells you something.
