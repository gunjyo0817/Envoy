/// <reference types="vite/client" />

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

let _authToken: string | null = null
export function setAuthToken(t: string | null) { _authToken = t }
export function authHeaders(): Record<string, string> {
  return _authToken ? { Authorization: `Bearer ${_authToken}` } : {}
}

export interface AuthUser { id: number; email: string; name: string; language: string; default_address: string; onboarded: boolean }
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

export function googleLoginUrl(): string {
  return `${BASE}/auth/google/login`
}

export async function fetchMe(): Promise<AuthUser> {
  const r = await fetch(`${BASE}/auth/me`, { headers: { ...authHeaders() } })
  if (!r.ok) throw new Error('Not authenticated')
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

export async function calendarStatus(): Promise<{ connected: boolean }> {
  const r = await fetch(`${BASE}/calendar/status`, { headers: { ...authHeaders() } })
  if (!r.ok) throw new Error('Failed to check calendar status')
  return r.json()
}

export async function calendarAuthUrl(): Promise<string> {
  const r = await fetch(`${BASE}/calendar/auth-url`, { headers: { ...authHeaders() } })
  if (!r.ok) throw new Error('Failed to start calendar connect')
  return (await r.json()).url
}

export async function addCalendarEvent(input: {
  summary: string; location: string; start_iso: string; end_iso: string
}): Promise<{ htmlLink: string }> {
  const r = await fetch(`${BASE}/calendar/event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(input),
  })
  if (r.status === 409) throw new Error('not_connected')
  if (!r.ok) throw new Error('Failed to add to calendar')
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
  url?: string
  image_url?: string
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

export interface Deal {
  session_id: string
  query: string | null
  thumbnail: string | null
  final_price: number | null
  seller_label: string | null
  meetup: Partial<MeetupProposal> | Record<string, never>
  status: string
  created_at: string
  closed_at: string
  negotiation_thread: NegotiationMessage[]
}

export async function listDeals(): Promise<Deal[]> {
  const r = await fetch(`${BASE}/deals`, { headers: { ...authHeaders() } })
  if (!r.ok) throw new Error('Failed to load history')
  return r.json()
}

export async function getDeal(sessionId: string): Promise<Deal> {
  const r = await fetch(`${BASE}/deals/${sessionId}`, { headers: { ...authHeaders() } })
  if (!r.ok) throw new Error('Failed to load deal')
  return r.json()
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
  query: string; budget_min: number; budget_max: number; condition: string;
  location: string; max_distance_km: number; language?: string
}): Promise<string> {
  const r = await fetch(`${BASE}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(params),
  })
  const data = await r.json()
  return data.session_id
}

function buildGeocodeUrl(baseUrl: string, lat: string, lng: string): string {
  try {
    const url = new URL(baseUrl);
    
    // Validate numeric parameters
    if (!/^-?[0-9]+(?:\.[0-9]+)?$/.test(lat)) {
      throw new Error('Invalid parameter');
    }
    if (!/^-?[0-9]+(?:\.[0-9]+)?$/.test(lng)) {
      throw new Error('Invalid parameter');
    }
    
    // Add query parameters
    url.searchParams.set('lat', lat);
    url.searchParams.set('lng', lng);
    
    return url.href;
  } catch {
    throw new Error('Invalid URL');
  }
}

export async function reverseGeocode(lat: number, lng: number): Promise<string> {
  const r = await fetch(buildGeocodeUrl(`${BASE}/geocode/reverse`, String(lat), String(lng)))
  if (!r.ok) throw new Error('Could not resolve location')
  const data = await r.json()
  return data.location ?? ''
}

export async function identifyImage(imageBase64: string): Promise<string> {
  const r = await fetch(`${BASE}/vision/identify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: imageBase64 }),
  })
  if (!r.ok) throw new Error('Could not identify the image')
  const data = await r.json()
  return data.query ?? ''
}

export interface VisionSearchResult {
  query: string
  matched_listing: {
    title?: string
    price_text?: string
    location?: string
    image_url?: string
    platform?: string
  } | null
}

export async function visionSearch(imageBase64: string): Promise<VisionSearchResult> {
  const r = await fetch(`${BASE}/vision/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: imageBase64 }),
  })
  if (!r.ok) throw new Error('Could not search from the image')
  return r.json()
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

export async function getFreebusy(timeMin: string, timeMax: string): Promise<{ busy: { start: string; end: string }[] }> {
  const r = await fetch(`${BASE}/calendar/freebusy?time_min=${encodeURIComponent(timeMin)}&time_max=${encodeURIComponent(timeMax)}`,
    { headers: { ...authHeaders() } })
  if (!r.ok) return { busy: [] }
  return r.json()
}

export async function proposeTimes(sessionId: string, slots: string[]): Promise<void> {
  await fetch(`${BASE}/session/${sessionId}/propose-times`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ slots }),
  })
}

export async function translateText(text: string, targetLang: string): Promise<string> {
  const r = await fetch(`${BASE}/translate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, target_lang: targetLang }),
  })
  if (!r.ok) return ''
  const data = await r.json()
  return data.translation ?? ''
}

export async function completeOnboarding(): Promise<AuthUser> {
  const r = await fetch(`${BASE}/onboarding/complete`, {
    method: 'POST', headers: { ...authHeaders() },
  })
  if (!r.ok) throw new Error('Failed to complete onboarding')
  return r.json()
}

export async function telegramLinkToken(): Promise<{ token: string; url: string }> {
  const r = await fetch(`${BASE}/telegram/link-token`, {
    method: 'POST', headers: { ...authHeaders() },
  })
  if (!r.ok) throw new Error('Failed to create Telegram link')
  return r.json()
}

export async function telegramStatus(): Promise<{ connected: boolean }> {
  const r = await fetch(`${BASE}/telegram/status`, { headers: { ...authHeaders() } })
  if (!r.ok) throw new Error('Failed to check Telegram status')
  return r.json()
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
