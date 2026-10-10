// Who's who on the desk: each agent has a name, a one-line role, an accent color, and an icon.
import type { AgentName } from './types'

export interface AgentMeta {
  id: AgentName
  name: string
  role: string
  color: string
  tint: string
}

export const AGENTS: AgentMeta[] = [
  { id: 'boss', name: 'Boss', role: 'Reads the ticket, makes the call', color: '#7b1e2b', tint: '#f6e8ea' },
  { id: 'inventory', name: 'Inventory', role: 'Stock, sizes, restock vendors', color: '#2f6b70', tint: '#e5f0f0' },
  { id: 'accounting', name: 'Accounting', role: 'Cash, invoices, margins', color: '#9a6a12', tint: '#f6eedc' },
  { id: 'facilities', name: 'Facilities', role: 'Leases, rent, the shop space', color: '#4c6a3a', tint: '#e9f0e3' },
  { id: 'customer_service', name: 'Customer Service', role: 'Drafts replies, never sends', color: '#8a4672', tint: '#f3e6ef' },
]

export const AGENT_BY_ID: Record<string, AgentMeta> = Object.fromEntries(AGENTS.map((a) => [a.id, a]))

const PATHS: Record<AgentName, string> = {
  boss: 'M4 17h16l-1.6-8.5-4.4 3.5L12 5.5 10 12 5.6 8.5Z M4 20h16',
  inventory: 'M3.5 7.5 12 3.5l8.5 4v9L12 20.5l-8.5-4Z M3.5 7.5 12 11.5l8.5-4 M12 11.5v9',
  accounting: 'M6 3.5h12v17l-3-2-3 2-3-2-3 2Z M9 8h6 M9 11.5h6 M9 15h3.5',
  facilities: 'M4 20.5V9l8-5.5L20 9v11.5 M9.5 20.5V15h5v5.5 M2.5 20.5h19',
  customer_service: 'M4 5h16v11H10l-5 4v-4H4Z M8 9.5h8 M8 12.5h5',
}

export function AgentIcon({ agent, size = 18 }: { agent: AgentName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[agent]} />
    </svg>
  )
}

export function AgentBadge({ agent, size = 34, pulse = false }: { agent: AgentName; size?: number; pulse?: boolean }) {
  const meta = AGENT_BY_ID[agent]
  return (
    <span className={`agent-badge${pulse ? ' pulse' : ''}`}
      style={{ width: size, height: size, background: meta.color, ['--ring' as string]: meta.color }}
      title={meta.name}>
      <AgentIcon agent={agent} size={Math.round(size * 0.55)} />
    </span>
  )
}

export const isAgent = (x: unknown): x is AgentName => typeof x === 'string' && x in AGENT_BY_ID
