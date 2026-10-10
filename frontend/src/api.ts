// Talks to the FastAPI backend from Problem 7.
import type { ApproveResult, Cash, EventsResponse, TicketsResponse } from './types'

export const API_BASE: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, init)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  return body as T
}

const post = (body?: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
})

export const api = {
  tickets: () => request<TicketsResponse>('/tickets'),
  cash: () => request<Cash>('/cash'),
  events: (after: number) => request<EventsResponse>(`/events?after=${after}&limit=1000`),
  run: (ticketId: number) => request<{ run_id: string }>(`/tickets/${ticketId}/run`, post()),
  approve: (requestId: number, approvedBy: string) =>
    request<ApproveResult>(`/payments/${requestId}/approve`, post({ approved_by: approvedBy })),
  reset: () => request<{ checking_balance: number }>('/reset', post()),
}
