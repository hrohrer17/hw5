import type { Ticket } from '../types'

const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

const TYPE_ICON: Record<string, string> = {
  customer_order: 'M6 8h12l-1 12H7Z M9 8a3 3 0 0 1 6 0',
  rent_notice: 'M4 20.5V9l8-5.5L20 9v11.5 M9.5 20.5V15h5v5.5',
  price_override: 'M3.5 12.5 11 5h8v8l-7.5 7.5Z M15 9h.01',
}

export function statusLabel(t: Ticket): { text: string; cls: string } {
  if (t.running) return { text: 'Agents working', cls: 'running' }
  if (t.status === 'resolved') return { text: 'Resolved', cls: 'resolved' }
  if (t.pending_requests.length || t.status === 'waiting_on_approval') return { text: 'Needs your approval', cls: 'approval' }
  if (t.status === 'in_progress') return { text: 'In progress', cls: 'progress' }
  return { text: 'Open', cls: 'open' }
}

function itemLine(t: Ticket) {
  if (t.sku) return `${t.qty ?? ''} × ${t.sku} · ${t.size ?? ''}`.trim()
  if (t.lease_id) return `Lease ${t.lease_id}`
  return t.type.replace('_', ' ')
}

interface Props {
  tickets: Ticket[]
  selected: number
  onSelect: (id: number) => void
}

export function TicketQueue({ tickets, selected, onSelect }: Props) {
  const resolved = tickets.filter((t) => t.status === 'resolved').length
  return (
    <aside className="queue">
      <div className="panel-head">
        <h2>Ticket queue</h2>
        <span className="muted">{resolved}/{tickets.length} resolved</span>
      </div>
      <div className="progress-track" aria-hidden="true">
        <div style={{ width: `${tickets.length ? (resolved / tickets.length) * 100 : 0}%` }} />
      </div>
      <ul className="ticket-list">
        {tickets.map((t) => {
          const st = statusLabel(t)
          return (
            <li key={t.id}>
              <button className={`ticket-card ${st.cls}${t.id === selected ? ' selected' : ''}`} onClick={() => onSelect(t.id)}>
                <span className="ticket-icon" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d={TYPE_ICON[t.type] ?? TYPE_ICON.customer_order} />
                  </svg>
                </span>
                <span className="ticket-main">
                  <span className="ticket-top">
                    <span className="ticket-id">#{t.id}</span>
                    <span className="ticket-type">{TYPE_LABEL[t.type] ?? t.type}</span>
                  </span>
                  <span className="ticket-subject">{t.subject}</span>
                  <span className="ticket-meta">{t.requester} · {itemLine(t)}</span>
                  <span className={`pill ${st.cls}`}>{st.text}</span>
                </span>
                {t.status === 'resolved' && <span className="seal" aria-label="Resolved">✓</span>}
              </button>
            </li>
          )
        })}
      </ul>
      <p className="queue-foot">
        Agents only <b>prepare</b> payments. Nothing leaves checking until you approve it.
      </p>
    </aside>
  )
}
