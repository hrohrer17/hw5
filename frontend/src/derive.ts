// Turns the raw audit-trail events into what the board shows: the latest run per ticket,
// each agent's live state, per-agent summaries, and the spending ledger.
import { AGENTS, isAgent } from './agents'
import type { AgentName, DeskEvent, Outcome, Ticket } from './types'

export function lastResetSeq(events: DeskEvent[]): number {
  let seq = -1
  for (const e of events) if (e.event === 'db_reset') seq = e.seq
  return seq
}

export interface RunView {
  runId: string
  startSeq: number
  finished: DeskEvent | null
  feed: DeskEvent[]
}

/** The newest run on this ticket since the last reset, plus any human approvals after it. */
export function latestRun(events: DeskEvent[], ticketId: number): RunView | null {
  const since = lastResetSeq(events)
  let start: DeskEvent | null = null
  for (const e of events) {
    if (e.seq > since && e.event === 'run_start' && e.ticket_id === ticketId) start = e
  }
  if (!start) return null
  const { run_id: runId, seq: startSeq } = start
  const feed = events.filter(
    (e) => e.run_id === runId || (e.event === 'human_approval' && e.ticket_id === ticketId && e.seq > startSeq),
  )
  const finished = feed.find((e) => e.event === 'run_finish') ?? null
  return { runId, startSeq, finished, feed }
}

export type AgentState = 'idle' | 'working' | 'tool' | 'waiting' | 'done'

export interface AgentLive {
  state: AgentState
  activity: string
  toolCalls: number
  tools: string[]
  worked: boolean
}

const HIDDEN_TOOLS = new Set(['delegate', 'final_result'])

/** Replay a run's events to get each agent's current state and what it has used. */
export function agentStates(run: RunView | null): Record<AgentName, AgentLive> {
  const out = {} as Record<AgentName, AgentLive>
  const idle = run?.finished ? 'Not needed on this ticket' : run ? 'Not called yet' : 'Ready for a ticket'
  for (const a of AGENTS) out[a.id] = { state: 'idle', activity: idle, toolCalls: 0, tools: [], worked: false }
  if (!run) return out
  for (const e of run.feed) {
    if (!isAgent(e.agent)) continue
    const s = out[e.agent]
    switch (e.event) {
      case 'agent_start':
        s.worked = true
        s.state = 'working'
        s.activity = 'Reading the task'
        break
      case 'model_request':
        if (s.state !== 'waiting') {
          s.state = 'working'
          s.activity = 'Thinking'
        }
        break
      case 'model_response': {
        const calls = (e.tool_calls ?? []).filter((c) => !HIDDEN_TOOLS.has(c.tool))
        const handoff = (e.tool_calls ?? []).find((c) => c.tool === 'delegate')
        for (const c of calls) {
          s.toolCalls += 1
          if (!s.tools.includes(c.tool)) s.tools.push(c.tool)
        }
        if (handoff) {
          const to = String(handoff.args.to_agent ?? '')
          s.state = 'waiting'
          s.activity = `Waiting on ${AGENTS.find((a) => a.id === to)?.name ?? to}`
        } else if (calls.length) {
          s.state = 'tool'
          s.activity = `Using ${calls.map((c) => c.tool).join(', ')}`
        } else if ((e.tool_calls ?? []).some((c) => c.tool === 'final_result')) {
          s.state = 'working'
          s.activity = 'Writing the final call'
        }
        break
      }
      case 'delegation_reply':
        s.state = 'working'
        s.activity = 'Reading the reply'
        break
      case 'agent_finish':
        s.state = 'done'
        s.activity = 'Done'
        break
    }
  }
  if (run.finished) {
    for (const a of AGENTS) {
      const s = out[a.id]
      if (s.worked) {
        s.state = 'done'
        s.activity = 'Done'
      } else s.activity = 'Not needed on this ticket'
    }
  }
  return out
}

export function outcomeFor(run: RunView | null, ticket: Ticket | undefined): Outcome | null {
  return run?.finished?.outcome ?? ticket?.last_run?.outcome ?? null
}

export interface AgentSummary {
  agent: AgentName
  text: string
  worked: boolean
}

/** One line per agent: the Boss's write-up, or what the trail shows, or "didn't do anything". */
export function agentSummaries(outcome: Outcome | null, live: Record<AgentName, AgentLive>): AgentSummary[] {
  return AGENTS.map((a) => {
    const fromBoss = (outcome?.contributions ?? []).filter((c) => c.agent === a.id).map((c) => c.contribution)
    if (fromBoss.length) return { agent: a.id, text: fromBoss.join(' '), worked: true }
    if (live[a.id].worked) {
      const used = live[a.id].tools.length ? ` Used ${live[a.id].tools.join(', ')}.` : ''
      return { agent: a.id, text: `Worked on this ticket.${used}`, worked: true }
    }
    return { agent: a.id, text: "Didn't do anything on this ticket.", worked: false }
  })
}

/** Money that left checking since the last reset (human approvals only). */
export function spending(events: DeskEvent[]): DeskEvent[] {
  const since = lastResetSeq(events)
  return events.filter((e) => e.event === 'human_approval' && e.seq > since)
}

export const money = (n: number | undefined | null, cents = false) =>
  n == null
    ? '—'
    : n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 })

export const kTokens = (n?: number) => (n == null ? '—' : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n))
