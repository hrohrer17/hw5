import { useState } from 'react'
import { AGENT_BY_ID, AgentBadge } from '../agents'
import { kTokens, money } from '../derive'
import type { AgentSummary } from '../derive'
import type { DeskEvent, Outcome, PaymentRequest, Ticket, Usage } from '../types'

const KIND: Record<string, string> = { invoice: 'Vendor invoice', rent: 'Rent', purchase_order: 'Purchase order' }

interface Props {
  ticket: Ticket | undefined
  outcome: Outcome | null
  usage: Usage | null | undefined
  summaries: AgentSummary[]
  hasRun: boolean
  running: boolean
  onApprove: (r: PaymentRequest) => void
  approving: number | null
  justPaid: number | null
  spent: DeskEvent[]
  approvals: DeskEvent[]
  baseline: number | null
  onReset: () => void
  canReset: boolean
}

export function SummaryPanel(p: Props) {
  const [copied, setCopied] = useState(false)
  const pending = p.ticket?.pending_requests ?? []
  const why = (id: number) => p.outcome?.approvals_needed.find((a) => a.request_id === id)?.why

  return (
    <aside className="side">
      {pending.length > 0 && (
        <section className="card approvals">
          <div className="card-head">
            <h3>Needs your approval</h3>
            <span className="count-badge">{pending.length}</span>
          </div>
          {pending.map((r) => (
            <div key={r.id} className={`approval${p.justPaid === r.id ? ' paid' : ''}`}>
              <div className="approval-top">
                <span className="approval-kind">{KIND[r.kind] ?? r.kind} · request #{r.id}</span>
                <span className="approval-amount">{money(r.amount, true)}</span>
              </div>
              <div className="approval-payee">to <b>{r.payee}</b>{r.qty ? ` · ${r.qty} × ${r.sku} ${r.size}` : ''}</div>
              <p className="approval-why">{why(r.id) ?? r.reason}</p>
              <div className="approval-foot">
                <span className="muted">Prepared by {r.requested_by}</span>
                <button className="approve-btn" onClick={() => p.onApprove(r)} disabled={p.approving !== null}>
                  {p.approving === r.id ? 'Paying…' : 'Approve & pay'}
                </button>
              </div>
              {p.justPaid === r.id && <span className="stamp">PAID</span>}
            </div>
          ))}
        </section>
      )}

      <section className="card">
        <div className="card-head">
          <h3>What each agent did</h3>
          {p.usage?.total_tokens != null && (
            <span className="muted" title="Model calls and tokens for this run (all agents)">
              {p.usage.requests} calls · {kTokens(p.usage.total_tokens)} tokens
            </span>
          )}
        </div>
        {!p.hasRun ? (
          <p className="muted">Run the team to see each agent's part.</p>
        ) : (
          <ul className="summaries">
            {p.summaries.map((s) => (
              <li key={s.agent} className={s.worked ? '' : 'idle'}>
                <AgentBadge agent={s.agent} size={26} />
                <div>
                  <div className="sum-name" style={{ color: AGENT_BY_ID[s.agent].color }}>{AGENT_BY_ID[s.agent].name}</div>
                  <div className="sum-text">{p.running && !s.worked ? 'Not called yet.' : s.text}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {p.outcome && (
        <section className="card outcome">
          <div className="card-head">
            <h3>Outcome</h3>
            <span className="muted">as of the end of the run</span>
          </div>
          <p>{p.outcome.outcome}</p>
          {p.approvals.length > 0 && (
            <div className="since">
              <b>Since then:</b>{' '}
              {p.approvals.map((a) => `${a.approved_by} approved ${money(a.amount, true)} to ${a.payee}`).join('; ')}.
              {p.ticket?.status === 'resolved' ? ' Ticket resolved.' : ''}
            </div>
          )}
          {p.outcome.follow_ups.length > 0 && (
            <>
              <div className="mini-head">Follow-ups</div>
              <ul className="follow">{p.outcome.follow_ups.map((f, i) => <li key={i}>{f}</li>)}</ul>
            </>
          )}
        </section>
      )}

      {p.outcome?.customer_message_draft && (
        <section className="card draft">
          <div className="card-head">
            <h3>Draft reply</h3>
            <span className="draft-tag">Draft · not sent</span>
          </div>
          <pre className="letter">{p.outcome.customer_message_draft}</pre>
          <button className="ghost-btn" onClick={() => {
            navigator.clipboard?.writeText(p.outcome?.customer_message_draft ?? '')
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
          }}>{copied ? 'Copied' : 'Copy draft'}</button>
        </section>
      )}

      <section className="card ledger">
        <div className="card-head"><h3>Cash out since reset</h3></div>
        {p.spent.length === 0 ? (
          <p className="muted">No payments yet{p.baseline != null ? ` · starting balance ${money(p.baseline)}` : ''}.</p>
        ) : (
          <ul className="ledger-list">
            {p.baseline != null && <li><span>Starting balance</span><b>{money(p.baseline, true)}</b></li>}
            {p.spent.map((e) => (
              <li key={e.seq}>
                <span>#{e.ticket_id} · {e.payee}</span>
                <b className="neg">−{money(e.amount, true)}</b>
              </li>
            ))}
            <li className="total"><span>Now</span><b>{money(p.spent[p.spent.length - 1].checking_after, true)}</b></li>
          </ul>
        )}
        <button className="ghost-btn danger" onClick={p.onReset} disabled={!p.canReset}>Reset the shop for a fresh run</button>
      </section>
    </aside>
  )
}
