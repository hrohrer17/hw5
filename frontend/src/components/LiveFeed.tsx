import { useEffect, useRef } from 'react'
import { AGENT_BY_ID, AgentBadge, isAgent } from '../agents'
import { kTokens, money } from '../derive'
import type { RunView } from '../derive'
import type { DeskEvent, Ticket, ToolCall } from '../types'
import { RichText } from './RichText'

const HIDDEN_TOOLS = new Set(['delegate', 'final_result'])
const SKIP_ARGS = new Set(['reason', 'requested_by', 'note'])

function argText(c: ToolCall) {
  const parts = Object.entries(c.args)
    .filter(([k]) => !SKIP_ARGS.has(k))
    .map(([k, v]) => `${k.replace(/_/g, ' ')} ${String(v)}`)
  return parts.join(' · ')
}

function Speaker({ agent, to }: { agent: string; to?: string }) {
  const meta = AGENT_BY_ID[agent]
  return (
    <div className="speaker">
      <span style={{ color: meta?.color }}>{meta?.name ?? agent}</span>
      {to && <span className="speaker-to">→ {AGENT_BY_ID[to]?.name ?? to}</span>}
    </div>
  )
}

function Row({ agent, children, depth = 0, kind = '' }: { agent: string; children: React.ReactNode; depth?: number; kind?: string }) {
  return (
    <li className={`row ${kind}`} style={{ ['--agent' as string]: AGENT_BY_ID[agent]?.color, ['--agent-tint' as string]: AGENT_BY_ID[agent]?.tint, ['--indent' as string]: `${Math.min(depth, 3) * 18}px` }}>
      {isAgent(agent) ? <AgentBadge agent={agent} size={30} /> : <span className="sys-dot" />}
      <div className="row-body">{children}</div>
    </li>
  )
}

function render(e: DeskEvent): React.ReactNode {
  switch (e.event) {
    case 'run_start':
      return <li key={e.seq} className="divider"><span>Run started · {e.model}</span></li>
    case 'agent_start':
      if (e.agent !== 'boss') return null
      return (
        <Row key={e.seq} agent="boss" kind="note">
          <Speaker agent="boss" />
          <p className="quiet">Opened the ticket and is reading it.</p>
        </Row>
      )
    case 'model_response': {
      const calls = (e.tool_calls ?? []).filter((c) => !HIDDEN_TOOLS.has(c.tool))
      if (!e.text && !calls.length) return null
      return (
        <Row key={e.seq} agent={e.agent} depth={e.depth}>
          <Speaker agent={e.agent} />
          {e.text && <div className="bubble"><RichText text={e.text} /></div>}
          {calls.map((c, i) => (
            <div key={i} className="tool-chip">
              <span className="wrench" aria-hidden="true">⚙</span>
              <code>{c.tool}</code>
              {argText(c) && <span className="tool-args">{argText(c)}</span>}
            </div>
          ))}
        </Row>
      )
    }
    case 'model_request': {
      const results = (e.parts ?? []).filter((p) => p.tool_result && !HIDDEN_TOOLS.has(p.tool_result))
      if (!results.length) return null
      return (
        <Row key={e.seq} agent={e.agent} depth={e.depth} kind="result">
          {results.map((p, i) => (
            <details key={i} className="result">
              <summary><code>{p.tool_result}</code> returned</summary>
              <pre>{JSON.stringify(p.content, null, 2)}</pre>
            </details>
          ))}
        </Row>
      )
    }
    case 'delegation':
      return (
        <Row key={e.seq} agent={e.agent} depth={e.depth} kind="handoff">
          <Speaker agent={e.agent} to={e.to_agent} />
          <div className="handoff-card">
            <span className="handoff-label">Hand-off</span>
            <RichText text={e.task ?? ''} />
          </div>
        </Row>
      )
    case 'delegation_reply':
      return (
        <Row key={e.seq} agent={e.from_agent ?? ''} depth={e.depth + 1} kind="reply">
          <Speaker agent={e.from_agent ?? ''} to={e.agent} />
          <div className="bubble reply"><RichText text={e.reply ?? ''} /></div>
        </Row>
      )
    case 'delegation_refused':
      return (
        <Row key={e.seq} agent={e.agent} depth={e.depth} kind="refused">
          <Speaker agent={e.agent} to={e.to_agent} />
          <p className="warn">Hand-off blocked: {e.reason}</p>
        </Row>
      )
    case 'agent_finish': {
      if (e.agent !== 'boss') return null
      const out = e.output as { boss_decision?: string } | null
      if (!out?.boss_decision) return null
      return (
        <Row key={e.seq} agent="boss" kind="final">
          <Speaker agent="boss" />
          <div className="final-card">
            <span className="handoff-label">Final call</span>
            <p>{out.boss_decision}</p>
          </div>
        </Row>
      )
    }
    case 'run_finish':
      return (
        <li key={e.seq} className="divider done">
          <span>
            Run finished{e.final_status ? ` · ${e.final_status.replace(/_/g, ' ')}` : ''}
            {e.usage ? ` · ${e.usage.requests} model calls · ${kTokens(e.usage.total_tokens)} tokens` : ''}
            {e.error ? ` · ${e.error}` : ''}
          </span>
        </li>
      )
    case 'human_approval':
      return (
        <li key={e.seq} className="human-row">
          <span className="stamp small">PAID</span>
          <span><b>{e.approved_by}</b> approved {money(e.amount, true)} to {e.payee}. Checking {money(e.checking_before)} → <b>{money(e.checking_after)}</b></span>
        </li>
      )
    default:
      return null
  }
}

interface Props {
  ticket: Ticket | undefined
  run: RunView | null
  running: boolean
  busyElsewhere: boolean
  onRun: () => void
  starting: boolean
}

export function LiveFeed({ ticket, run, running, busyElsewhere, onRun, starting }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const count = run?.feed.length ?? 0
  useEffect(() => {
    // Follow the conversation inside its own box only; never scroll the whole page.
    const box = scrollRef.current
    if (running && box) box.scrollTo({ top: box.scrollHeight, behavior: 'smooth' })
  }, [count, running])

  const resolved = ticket?.status === 'resolved'
  const canRun = !!ticket && !running && !busyElsewhere && !resolved && !starting
  return (
    <section className="feed-panel">
      <div className="feed-head">
        <div>
          <div className="eyebrow">Ticket #{ticket?.id} · {ticket?.requester}</div>
          <h2>{ticket?.subject ?? 'Pick a ticket'}</h2>
          {ticket?.notes && <p className="ticket-quote">"{ticket.notes.split('\n')[0]}"</p>}
        </div>
        <button className="run-btn" onClick={onRun} disabled={!canRun}>
          {running ? <><span className="spinner" /> Team at work…</> :
            starting ? 'Starting…' :
            resolved ? 'Resolved ✓' :
            busyElsewhere ? 'Another ticket is running' :
            run ? 'Run the team again' : 'Run the team'}
        </button>
      </div>

      <div className="feed-scroll" ref={scrollRef}>
        {!run ? (
          <div className="empty">
            <div className="empty-title">The team hasn't touched this ticket yet.</div>
            <p>Press <b>Run the team</b> and the Boss will read it, hand pieces to the right teammates, and make the call. You'll see every message, hand-off, and tool call here as it happens.</p>
          </div>
        ) : (
          <ol className="feed">
            {run.feed.map(render)}
            {running && (
              <li className="typing"><span /><span /><span /></li>
            )}
          </ol>
        )}
      </div>
    </section>
  )
}
