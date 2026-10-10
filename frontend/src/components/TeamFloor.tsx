import { AGENTS, AgentBadge } from '../agents'
import type { AgentLive } from '../derive'
import type { AgentName } from '../types'

const STATE_TEXT: Record<string, string> = {
  idle: 'Idle',
  working: 'Working',
  tool: 'Using a tool',
  waiting: 'Waiting',
  done: 'Done',
}

export function TeamFloor({ live, chain }: { live: Record<AgentName, AgentLive>; chain: AgentName[] }) {
  return (
    <section className="floor" aria-label="The agent team">
      {AGENTS.map((a) => {
        const s = live[a.id]
        const active = s.state === 'working' || s.state === 'tool'
        const inChain = chain.includes(a.id)
        return (
          <div key={a.id} className={`desk ${s.state}${inChain ? ' in-chain' : ''}${s.activity === 'Not needed on this ticket' ? ' benched' : ''}`}
            style={{ ['--agent' as string]: a.color, ['--agent-tint' as string]: a.tint }}>
            <AgentBadge agent={a.id} size={38} pulse={active} />
            <div className="desk-text">
              <div className="desk-name">{a.name}</div>
              <div className="desk-role">{a.role}</div>
              <div className="desk-activity">
                <span className={`dot ${s.state}`} />
                <span>{s.state === 'idle' ? s.activity : `${STATE_TEXT[s.state]} · ${s.activity}`}</span>
              </div>
            </div>
            {s.toolCalls > 0 && <span className="desk-count" title="Tool calls on this ticket">{s.toolCalls}</span>}
          </div>
        )
      })}
    </section>
  )
}
