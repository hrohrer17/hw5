import { useEffect, useRef, useState } from 'react'
import { money } from '../derive'
import type { Cash } from '../types'

/** Counts smoothly from the old balance to the new one so a payment is felt, not just seen. */
function useTween(target: number | undefined, ms = 900): number | undefined {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    if (target === undefined) return
    const start = from.current ?? target
    if (start === target) {
      setShown(target)
      return
    }
    const t0 = performance.now()
    let raf = 0
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / ms)
      const eased = 1 - Math.pow(1 - k, 3)
      setShown(start + (target - start) * eased)
      if (k < 1) raf = requestAnimationFrame(step)
      else from.current = target
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return shown
}

function shopDate(iso?: string) {
  if (!iso) return '—'
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}

interface Props {
  cash: Cash | null
  baseline: number | null
  shopDateIso?: string
  approver: string
  onApprover: (v: string) => void
  approverRef: React.RefObject<HTMLInputElement | null>
  dropped: boolean
}

export function TopBar({ cash, baseline, shopDateIso, approver, onApprover, approverRef, dropped }: Props) {
  const shown = useTween(cash?.balance)
  const base = baseline && baseline > 0 ? baseline : cash?.balance ?? 1
  const filled = cash ? Math.max(0, Math.min(1, cash.balance / base)) : 0
  const promised = cash ? Math.max(0, Math.min(filled, cash.pending_requests_total / base)) : 0

  return (
    <header className="topbar">
      <div className="brand">
        <div className="crest" aria-hidden="true">CC</div>
        <div>
          <div className="brand-name">Campus Customs</div>
          <div className="brand-sub">Back-office desk · Chapel Street</div>
        </div>
      </div>

      <div className="shop-clock" title="The shop's 'today' (desk.date_today). Agents judge overdue and due dates against this, not the real calendar.">
        <span className="label">Shop date</span>
        <span className="value">{shopDate(shopDateIso)}</span>
      </div>

      <label className="approver">
        <span className="label">Approving as</span>
        <input ref={approverRef} value={approver} placeholder="Your name"
          onChange={(e) => onApprover(e.target.value)} aria-label="Your name for approvals" />
      </label>

      <div className={`cash${dropped ? ' dropped' : ''}`} aria-live="polite">
        <div className="cash-row">
          <span className="label">Checking</span>
          <span className="cash-amount">{shown === undefined ? '—' : money(shown)}</span>
        </div>
        <div className="cash-bar" title={cash ? `${money(cash.balance)} of ${money(base)} starting balance` : ''}>
          <div className="cash-fill" style={{ width: `${filled * 100}%` }}>
            <div className="cash-promised" style={{ width: filled ? `${(promised / filled) * 100}%` : 0 }} />
          </div>
        </div>
        <div className="cash-note">
          {cash
            ? cash.pending_requests_total > 0
              ? <>{money(cash.pending_requests_total)} promised · <b>{money(cash.available_after_pending)}</b> free</>
              : <>Nothing waiting on approval</>
            : 'Connecting…'}
        </div>
      </div>
    </header>
  )
}
