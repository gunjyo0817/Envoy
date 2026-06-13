/// <reference types="vite/client" />

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

let _authToken: string | null = null
export function setAuthToken(t: string | null) { _authToken = t }
export function authHeaders(): Record<string, string> {
  return _authToken ? { Authorization: `Bearer ${_authToken}` } : {}
}

export interface AuthUser { id: number; email: string; name: string; language: string; default_address: string }
export interface AuthResult { token: string; user: AuthUser }

export async function signup(email: string, password: string, name: string): Promise<AuthResult> {
  const r = await fetch(`${BASE}/auth/signup`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name }),
  })
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Sign up failed')
  return r.json()
}

export async function login(email: string, password: string): Promise<AuthResult> {
  const r = await fetch(`${BASE}/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || 'Login failed')
  return r.json()
}

export interface UserSettings { language: string; default_address: string }

export async function getSettings(): Promise<UserSettings> {
  const r = await fetch(`${BASE}/settings`, { headers: { ...authHeaders() } })
  if (!r.ok) throw new Error('Failed to load settings')
  return r.json()
}

export async function updateSettings(patch: Partial<UserSettings>): Promise<UserSettings> {
  const r = await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(patch),
  })
  if (!r.ok) throw new Error('Failed to save settings')
  return r.json()
}

export interface SessionState {
  query?: string
  budget?: number
  status?: string
  ranked_candidates?: Candidate[]
  current_candidate_index?: number
  pending_decision?: PendingDecision | null
  negotiation_thread?: NegotiationMessage[]
  meetup_proposal?: MeetupProposal | null
  final_price?: number | null
  degraded?: string[]
  decision_history?: DecisionEntry[]
}

export interface Candidate {
  title: string
  price_eur: number
  condition: string
  score: number
  seller_rating: number | null
  seller_reviews: number | null
  location: string
  platform: string
  insight?: string
}

export interface PendingDecision {
  checkpoint: string
  summary: string
  options: Array<{ id: string; label: string }>
  context: Record<string, unknown>
}

export interface NegotiationMessage {
  role: 'buyer' | 'seller'
  text: string
  act: string
  price: number | null
  ts: string
}

export interface MeetupProposal {
  location: string
  time_suggestion: string
  reason: string
  buyer_route: { duration_text: string }
  seller_location: string
  final_price: number
}

export interface DecisionEntry {
  checkpoint: string
  choice: string
  ts: string
}

export interface WsEvent {
  event: 'state_changed' | 'agent_log'
  status?: string
  agent?: string
  msg?: string
}

export async function createSession(params: {
  query: string; budget: number; condition: string;
  location: string; max_distance_km: number
}): Promise<string> {
  const r = await fetch(`${BASE}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  const data = await r.json()
  return data.session_id
}

export async function getState(sessionId: string): Promise<SessionState> {
  const r = await fetch(`${BASE}/session/${sessionId}/state`)
  return r.json()
}

export async function postFeedback(
  sessionId: string, choice: string, freeText?: string
): Promise<void> {
  await fetch(`${BASE}/session/${sessionId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ choice, free_text: freeText ?? null }),
  })
}

export function connectWS(
  sessionId: string,
  onEvent: (e: WsEvent) => void
): () => void {
  const ws = new WebSocket(`${BASE.replace('http', 'ws')}/session/${sessionId}/stream`)
  ws.onmessage = (e) => onEvent(JSON.parse(e.data))
  ws.onerror = () => {}
  return () => ws.close()
}
