// Shapes returned by the desk API (backend/main.py).

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export type TicketStatus = 'open' | 'in_progress' | 'waiting_on_approval' | 'resolved'

export interface PaymentRequest {
  id: number
  kind: 'invoice' | 'rent' | 'purchase_order'
  ref_id: number | null
  payee: string
  amount: number
  sku: string | null
  size: string | null
  qty: number | null
  ticket_id: number | null
  reason: string
  requested_by: string
  status: 'pending' | 'approved' | 'declined'
  created_at: string
}

export interface Contribution {
  agent: AgentName
  contribution: string
}

export interface ApprovalNeeded {
  request_id: number
  kind: string
  payee: string
  amount: number
  why: string
}

export interface Outcome {
  ticket_id: number
  final_status: TicketStatus
  outcome: string
  boss_decision: string
  contributions: Contribution[]
  approvals_needed: ApprovalNeeded[]
  customer_message_draft: string | null
  follow_ups: string[]
}

export interface Usage {
  requests?: number
  tool_calls?: number
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
}

export interface LastRun {
  run_id: string
  finished_at: string | null
  error: string | null
  outcome: Outcome | null
  usage: Usage | null
}

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: TicketStatus
  created_at: string
  notes: string | null
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  state: 'open' | 'resolved'
  pending_requests: PaymentRequest[]
  running: boolean
  last_run: LastRun | null
}

export interface RunningInfo {
  run_id: string
  ticket_id: number
  model: string
}

export interface TicketsResponse {
  shop_date_today: string
  running: RunningInfo | null
  tickets: Ticket[]
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  pending_requests_total: number
  available_after_pending: number
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
}

export interface DeskEvent {
  seq: number
  summary: string
  ts: string
  run_id: string
  ticket_id: number | null
  agent: string
  depth: number
  step: number | null
  event: string
  // event-specific fields (see backend/team.py and main.py)
  text?: string | null
  tool_calls?: ToolCall[]
  parts?: Array<{ tool_result?: string; retry?: string; user_prompt?: string; content?: unknown }>
  to_agent?: AgentName
  from_agent?: AgentName
  task?: string
  reply?: string
  reason?: string
  prompt?: string
  output?: unknown
  outcome?: Outcome | null
  usage?: Usage
  final_status?: TicketStatus | null
  error?: string | null
  model?: string
  approved_by?: string
  amount?: number
  payee?: string
  kind?: string
  checking_before?: number
  checking_after?: number
  checking_after_reset?: number
  request_id?: number
}

export interface EventsResponse {
  last_seq: number
  running: RunningInfo | null
  events: DeskEvent[]
}

export interface ApproveResult {
  approved: boolean
  payment_id: number
  amount: number
  payee: string
  checking_before: number
  checking_after: number
  ticket_update: { updated: boolean; new_status: string } | null
}
