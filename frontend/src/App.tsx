import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, API_BASE } from './api'
import { isAgent } from './agents'
import { agentStates, agentSummaries, latestRun, outcomeFor, spending } from './derive'
import type { AgentName, Cash, DeskEvent, PaymentRequest, TicketsResponse } from './types'
import { LiveFeed } from './components/LiveFeed'
import { SummaryPanel } from './components/SummaryPanel'
import { TeamFloor } from './components/TeamFloor'
import { TicketQueue } from './components/TicketQueue'
import { TopBar } from './components/TopBar'

type Toast = { kind: 'ok' | 'err'; text: string } | null

export default function App() {
  const [desk, setDesk] = useState<TicketsResponse | null>(null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [events, setEvents] = useState<DeskEvent[]>([])
  const lastSeq = useRef(-1)
  const [selected, setSelected] = useState(101)
  const [approver, setApprover] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const approverRef = useRef<HTMLInputElement>(null)
  const [offline, setOffline] = useState(false)
  const [toast, setToast] = useState<Toast>(null)
  const [starting, setStarting] = useState(false)
  const [approving, setApproving] = useState<number | null>(null)
  const [justPaid, setJustPaid] = useState<number | null>(null)
  const [dropped, setDropped] = useState(false)

  const flash = useCallback((t: Toast) => {
    setToast(t)
    setTimeout(() => setToast(null), 4200)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [t, c] = await Promise.all([api.tickets(), api.cash()])
      setDesk(t)
      setCash(c)
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [])

  const polling = useRef(false)
  const pollEvents = useCallback(async () => {
    if (polling.current) return // one poll at a time (StrictMode and timers can overlap)
    polling.current = true
    try {
      const r = await api.events(lastSeq.current)
      if (r.events.length) {
        lastSeq.current = Math.max(lastSeq.current, r.events[r.events.length - 1].seq)
        setEvents((prev) => {
          const last = prev.length ? prev[prev.length - 1].seq : -1
          return [...prev, ...r.events.filter((e) => e.seq > last)]
        })
      }
    } catch {
      setOffline(true)
    } finally {
      polling.current = false
    }
  }, [])

  const running = desk?.running ?? null

  // Faster polling while agents are working so the conversation streams in.
  useEffect(() => {
    refresh()
    pollEvents()
    const ev = setInterval(pollEvents, running ? 900 : 4000)
    const st = setInterval(refresh, running ? 2000 : 5000)
    return () => {
      clearInterval(ev)
      clearInterval(st)
    }
  }, [running, refresh, pollEvents])

  // When a run finishes, pull the final state right away.
  const wasRunning = useRef<number | null>(null)
  useEffect(() => {
    if (wasRunning.current !== null && !running) {
      const id = wasRunning.current
      refresh()
      pollEvents()
      flash({ kind: 'ok', text: `Ticket #${id}: the team has finished.` })
    }
    wasRunning.current = running?.ticket_id ?? null
  }, [running, refresh, pollEvents, flash])

  useEffect(() => {
    localStorage.setItem('cc-approver', approver)
  }, [approver])

  const tickets = desk?.tickets ?? []
  const ticket = tickets.find((t) => t.id === selected)
  const run = useMemo(() => latestRun(events, selected), [events, selected])
  const live = useMemo(() => agentStates(run), [run])
  const outcome = outcomeFor(run, ticket)
  const summaries = useMemo(() => agentSummaries(outcome, live), [outcome, live])
  const spent = useMemo(() => spending(events), [events])
  const baseline = cash ? cash.balance + spent.reduce((s, e) => s + (e.amount ?? 0), 0) : null
  const runningHere = running?.ticket_id === selected
  const usage = run?.finished?.usage ?? ticket?.last_run?.usage

  // The hand-off chain currently waiting (e.g. Boss → Facilities → Accounting).
  const chain = useMemo(() => {
    if (!runningHere) return [] as AgentName[]
    return (Object.keys(live) as AgentName[]).filter((a) => live[a].state === 'waiting' || live[a].state === 'working' || live[a].state === 'tool')
  }, [live, runningHere])

  async function startRun() {
    if (!ticket) return
    setStarting(true)
    try {
      await api.run(ticket.id)
      await refresh()
      await pollEvents()
    } catch (e) {
      flash({ kind: 'err', text: (e as Error).message })
    } finally {
      setStarting(false)
    }
  }

  async function approve(r: PaymentRequest) {
    const who = approver.trim()
    if (!who) {
      approverRef.current?.focus()
      flash({ kind: 'err', text: 'Type your name in "Approving as" first, so the payment records who approved it.' })
      return
    }
    setApproving(r.id)
    try {
      const res = await api.approve(r.id, who)
      setJustPaid(r.id)
      setDropped(true)
      setCash((c) => (c ? { ...c, balance: res.checking_after, pending_requests_total: Math.max(0, c.pending_requests_total - res.amount) } : c))
      flash({ kind: 'ok', text: `Paid ${res.payee} $${res.amount.toLocaleString()}.${res.ticket_update?.new_status === 'resolved' ? ` Ticket #${r.ticket_id} is resolved.` : ''}` })
      setTimeout(async () => {
        setJustPaid(null)
        setDropped(false)
        await refresh()
        await pollEvents()
      }, 1800)
    } catch (e) {
      flash({ kind: 'err', text: (e as Error).message })
    } finally {
      setApproving(null)
    }
  }

  async function reset() {
    if (!window.confirm('Reset the shop? This copies the original database back over the working copy (cash back to the start, tickets reopened). The audit trail is kept.')) return
    try {
      const r = await api.reset()
      await refresh()
      await pollEvents()
      flash({ kind: 'ok', text: `Shop reset. Checking is back to $${r.checking_balance.toLocaleString()}.` })
    } catch (e) {
      flash({ kind: 'err', text: (e as Error).message })
    }
  }

  return (
    <div className="app">
      <TopBar cash={cash} baseline={baseline} shopDateIso={desk?.shop_date_today} approver={approver}
        onApprover={setApprover} approverRef={approverRef} dropped={dropped} />

      {offline && (
        <div className="offline">
          Can't reach the desk API at <code>{API_BASE}</code>. Start it from <code>backend/</code> with <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="layout">
        <TicketQueue tickets={tickets} selected={selected} onSelect={setSelected} />

        <div className="center">
          <TeamFloor live={live} chain={chain.filter(isAgent)} />
          <LiveFeed ticket={ticket} run={run} running={runningHere} busyElsewhere={!!running && !runningHere}
            onRun={startRun} starting={starting} />
        </div>

        <SummaryPanel ticket={ticket} outcome={outcome} usage={usage} summaries={summaries} hasRun={!!run || !!outcome}
          running={runningHere} onApprove={approve} approving={approving} justPaid={justPaid}
          spent={spent} approvals={run?.feed.filter((e) => e.event === 'human_approval') ?? []} baseline={baseline} onReset={reset} canReset={!running} />
      </main>

      {toast && <div className={`toast ${toast.kind}`} role="status">{toast.text}</div>}
    </div>
  )
}
