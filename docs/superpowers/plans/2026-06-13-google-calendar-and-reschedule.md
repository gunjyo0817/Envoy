# Google Calendar Integration + Interactive Reschedule (Plan C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the buyer's Google Calendar (offline OAuth), use freebusy so scheduling avoids busy times, let the buyer write a confirmed meetup back to Google Calendar from the Done screen and History detail, and make "Suggest different time" an interactive two-sided flow (buyer picks free slots → seller picks one on Telegram).

**Architecture:** Three risk-ordered phases. **Phase 1** adds offline Google OAuth + a `google_tokens` store + a refresh helper, exposed through a "Connect Google Calendar" action in Settings. **Phase 2** adds an "Add to Google Calendar" write-back (a datetime-picker → `events.insert`) on the Done screen and History detail. **Phase 3** adds a freebusy endpoint and an interactive reschedule: a week picker (busy slots greyed) whose chosen slots are sent to the seller on Telegram via the same async-interrupt pattern as the seller turn. Calendar REST calls use raw `httpx` (no new deps), mirroring the existing Telegram/Gemini style.

**Tech Stack:** Python FastAPI + httpx + stdlib sqlite3 · LangGraph 1.2 (`interrupt`/`Command`) · React 19 + Vite + TS + Tailwind 4 + react-router-dom 7 · Google OAuth2 + Calendar v3 REST.

**Builds on Plans A+B (merged to `main`).** Reuses: `store.py` (sqlite + deals + telegram_links), `telegram.py` (`tg_send`, `notify_seller`, `poll_updates`, `_dispatch`), `main.py` (`_run_graph` interrupt-bridge, `_on_state_committed`, `_resume_seller`, `_require_user`, `_sessions` with `user_id`), the seller-turn async pattern in `graph.py`/`negotiate.py`, and `coordinate.py` (`plan_meetup_node`/`confirm_meetup_node`).

**Scope note (per writing-plans):** This is large and spans three subsystems. It is intentionally one plan (per request) but is phased so Phase 3 can be deferred without affecting Phases 1–2. Implement in order; each phase leaves the app working.

**Demo-prep prerequisites (not code):**
- In Google Cloud console, add `http://localhost:8000/calendar/callback` (and the deployed equivalent) to the OAuth client's Authorized redirect URIs.
- Ensure the OAuth consent screen has the Calendar scope enabled (test users added if the app is unverified).

---

## Decisions baked in

- **OAuth scope:** request `https://www.googleapis.com/auth/calendar` (full) alongside the existing `openid email profile`, with `access_type=offline` + `prompt=consent` to obtain a refresh token. Full scope reliably covers both `freeBusy.query` and `events.insert` (avoids scope-mismatch debugging mid-demo).
- **Calendar connection is a separate, explicit action** (not folded into Google *login*), because users may sign up via email/password. A logged-in user taps "Connect Google Calendar" in Settings.
- **OAuth state ↔ user mapping:** a random `state` is stored server-side (`_oauth_states: dict[str,int]`) mapping to the app `user_id`, verified on callback. The app bearer token is never placed in a URL.
- **Event time:** the write-back opens a datetime picker (default: tomorrow 15:00 local), creates a 30-minute event. The user controls the exact time.
- **Reschedule (Phase 3):** buyer proposes 2–3 free slots → seller picks one on Telegram → buyer re-confirms the concrete time. Mirrors the seller-turn interrupt pattern.

---

## File Structure

- `backend/app/store.py` (modify) — `google_tokens` table + `save_google_tokens`/`get_google_tokens`/`update_google_access`.
- `backend/app/gcal.py` (**new**) — Google OAuth + Calendar REST: `auth_url`, `exchange_code`, `valid_access_token` (refresh), `query_freebusy`, `insert_event`. One responsibility: Google Calendar I/O.
- `backend/app/main.py` (modify) — `_oauth_states`; endpoints `/calendar/auth-url`, `/calendar/callback`, `/calendar/status`, `/calendar/freebusy`, `/calendar/event`, `/session/{id}/propose-times`; bridge handling for the `seller_time` checkpoint.
- `backend/app/agents/coordinate.py` (modify) — `confirm_meetup_node` handles a structured reschedule; new `seller_time_turn_node`.
- `backend/app/graph.py` (modify) — register `seller_time_turn` + routing.
- `backend/app/telegram.py` (modify) — `notify_seller_time(session_id, pending)` + `time:` callback routing in `_dispatch`.
- `frontend/src/api.ts` (modify) — calendar + propose-times clients.
- `frontend/src/components/AddToCalendar.tsx` (**new**) — datetime picker + "Add to Google Calendar".
- `frontend/src/components/WeekPicker.tsx` (**new**) — 7-day slot grid, busy slots greyed.
- `frontend/src/screens/SettingsScreen.tsx`, `DoneScreen.tsx`, `MeetupScreen.tsx`, `HistoryScreen.tsx` (modify) — wire the above in.
- Tests: `backend/tests/test_google_tokens.py`, `test_gcal.py`, `test_calendar_api.py`, `test_reschedule.py` (**new**).

---

# PHASE 1 — Calendar connection

## Task 1: `google_tokens` persistence

**Files:** Modify `backend/app/store.py`; Test `backend/tests/test_google_tokens.py` (new).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_google_tokens.py
import os, tempfile, importlib


def _fresh_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["ENVOY_DB"] = path
    import app.store as store
    importlib.reload(store)
    store.init_store()
    return store


def test_google_tokens_roundtrip_and_refresh_update():
    store = _fresh_store()
    store.save_google_tokens(user_id=3, access_token="a1", refresh_token="r1",
                             expiry="2026-06-13T12:00:00+00:00", scope="calendar")
    tok = store.get_google_tokens(3)
    assert tok["access_token"] == "a1" and tok["refresh_token"] == "r1"
    store.update_google_access(3, access_token="a2", expiry="2026-06-13T13:00:00+00:00")
    tok = store.get_google_tokens(3)
    assert tok["access_token"] == "a2" and tok["refresh_token"] == "r1"  # refresh token preserved


def test_get_google_tokens_missing_returns_none():
    store = _fresh_store()
    assert store.get_google_tokens(999) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_google_tokens.py -v`
Expected: FAIL — `AttributeError: module 'app.store' has no attribute 'save_google_tokens'`.

- [ ] **Step 3: Implement in `backend/app/store.py`**

(a) In `init_store()`, add a third `CREATE TABLE` inside the `with _connect() as conn:` block:
```python
        conn.execute(
            """CREATE TABLE IF NOT EXISTS google_tokens (
                user_id       INTEGER PRIMARY KEY,
                access_token  TEXT,
                refresh_token TEXT,
                expiry        TEXT,
                scope         TEXT
            )"""
        )
```

(b) Add the functions (anywhere after `get_deal`):
```python
def save_google_tokens(user_id: int, access_token: str, refresh_token: str | None,
                       expiry: str, scope: str) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO google_tokens (user_id, access_token, refresh_token, expiry, scope)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 access_token=excluded.access_token,
                 refresh_token=COALESCE(excluded.refresh_token, google_tokens.refresh_token),
                 expiry=excluded.expiry, scope=excluded.scope""",
            (user_id, access_token, refresh_token, expiry, scope),
        )


def update_google_access(user_id: int, access_token: str, expiry: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE google_tokens SET access_token=?, expiry=? WHERE user_id=?",
            (access_token, expiry, user_id),
        )


def get_google_tokens(user_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM google_tokens WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else None
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_google_tokens.py tests/test_store.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/store.py backend/tests/test_google_tokens.py
git commit -m "feat: google_tokens persistence"
```

---

## Task 2: `gcal.py` — OAuth + token refresh

**Files:** Create `backend/app/gcal.py`; Test `backend/tests/test_gcal.py` (new).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_gcal.py
import os, importlib, datetime
from unittest.mock import patch, MagicMock


def _store_with_token(expiry_iso):
    import app.store as store
    importlib.reload(store)
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd)
    os.environ["ENVOY_DB"] = path
    importlib.reload(store); store.init_store()
    store.save_google_tokens(1, "old", "refresh-1", expiry_iso, "calendar")
    return store


def test_auth_url_contains_offline_and_scope():
    import app.gcal as gcal
    url = gcal.auth_url("state-xyz")
    assert "access_type=offline" in url and "prompt=consent" in url
    assert "calendar" in url and "state=state-xyz" in url


def test_valid_access_token_returns_current_when_not_expired():
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
    store = _store_with_token(future)
    import app.gcal as gcal
    importlib.reload(gcal)
    with patch("app.gcal.store", store):
        assert gcal.valid_access_token(1) == "old"


def test_valid_access_token_refreshes_when_expired():
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
    store = _store_with_token(past)
    import app.gcal as gcal
    importlib.reload(gcal)
    resp = MagicMock(); resp.json.return_value = {"access_token": "new", "expires_in": 3600}
    resp.raise_for_status.return_value = None
    with patch("app.gcal.store", store), patch("app.gcal.httpx.post", return_value=resp) as post:
        tok = gcal.valid_access_token(1)
    assert tok == "new"
    assert store.get_google_tokens(1)["access_token"] == "new"
    body = post.call_args[1]["data"]
    assert body["grant_type"] == "refresh_token" and body["refresh_token"] == "refresh-1"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_gcal.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.gcal'`.

- [ ] **Step 3: Implement `backend/app/gcal.py`**

```python
"""Google OAuth + Calendar v3 REST via raw httpx. No google client lib."""
import os, datetime, urllib.parse
import httpx
from app import store

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_CALENDAR_REDIRECT_URI", "http://localhost:8000/calendar/callback")
SCOPE = "openid email profile https://www.googleapis.com/auth/calendar"
TZ = os.environ.get("ENVOY_TZ", "Europe/Berlin")

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CAL = "https://www.googleapis.com/calendar/v3"


def auth_url(state: str) -> str:
    params = {
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def _expiry_from_now(seconds: int) -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(seconds=seconds)).isoformat()


def exchange_code(code: str) -> dict:
    """Exchange an auth code → {access_token, refresh_token, expiry}."""
    resp = httpx.post(_TOKEN_URL, data={
        "code": code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code",
    }, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expiry": _expiry_from_now(int(data.get("expires_in", 3600))),
    }


def valid_access_token(user_id: int) -> str | None:
    """Return a non-expired access token, refreshing via the refresh token if needed."""
    tok = store.get_google_tokens(user_id)
    if not tok:
        return None
    try:
        expiry = datetime.datetime.fromisoformat(tok["expiry"])
    except (ValueError, TypeError):
        expiry = datetime.datetime.now(datetime.timezone.utc)
    if expiry > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60):
        return tok["access_token"]
    if not tok.get("refresh_token"):
        return tok["access_token"]
    resp = httpx.post(_TOKEN_URL, data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "refresh_token": tok["refresh_token"], "grant_type": "refresh_token",
    }, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    new_access = data["access_token"]
    store.update_google_access(user_id, new_access, _expiry_from_now(int(data.get("expires_in", 3600))))
    return new_access


def query_freebusy(user_id: int, time_min_iso: str, time_max_iso: str) -> list[dict]:
    """Return the user's busy intervals [{start, end}] in the window, or [] if unavailable."""
    token = valid_access_token(user_id)
    if not token:
        return []
    try:
        resp = httpx.post(f"{_CAL}/freeBusy", headers={"Authorization": f"Bearer {token}"},
                          json={"timeMin": time_min_iso, "timeMax": time_max_iso,
                                "items": [{"id": "primary"}]}, timeout=10.0)
        resp.raise_for_status()
        return resp.json()["calendars"]["primary"].get("busy", [])
    except Exception:
        return []


def insert_event(user_id: int, summary: str, location: str,
                 start_iso: str, end_iso: str) -> dict | None:
    """Insert a calendar event; return {htmlLink} or None if not connected/failed."""
    token = valid_access_token(user_id)
    if not token:
        return None
    resp = httpx.post(
        f"{_CAL}/calendars/primary/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "summary": summary, "location": location,
            "start": {"dateTime": start_iso, "timeZone": TZ},
            "end": {"dateTime": end_iso, "timeZone": TZ},
        }, timeout=10.0)
    resp.raise_for_status()
    return {"htmlLink": resp.json().get("htmlLink")}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_gcal.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/gcal.py backend/tests/test_gcal.py
git commit -m "feat: google oauth + calendar REST helpers"
```

---

## Task 3: Calendar connect/callback/status endpoints

**Files:** Modify `backend/app/main.py`; Test `backend/tests/test_calendar_api.py` (new).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_calendar_api.py
import importlib
from unittest.mock import patch
from fastapi.testclient import TestClient


def _client():
    import app.main as main
    importlib.reload(main)
    return main, TestClient(main.app)


def test_auth_url_requires_user_and_returns_url():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.gcal.auth_url", lambda state: f"https://google/auth?state={state}"):
            r = client.get("/calendar/auth-url")
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://google/auth?state=")
    # the state must have been registered to the user
    state = r.json()["url"].split("state=")[1]
    assert main._oauth_states[state] == 4


def test_status_reports_connected():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.store.get_google_tokens", return_value={"access_token": "a"}):
            r = client.get("/calendar/status")
    finally:
        main.app.dependency_overrides.clear()
    assert r.json() == {"connected": True}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_calendar_api.py -v`
Expected: FAIL — 404 (routes absent).

- [ ] **Step 3: Implement in `backend/app/main.py`**

(a) Add imports near the others: `from app import gcal` and `import secrets` (check `secrets` isn't already imported; add if missing). Add a module-level state map after `_sessions`:
```python
_oauth_states: dict[str, int] = {}   # oauth state → app user_id
```

(b) Add endpoints (after the settings/deals endpoints):
```python
@app.get("/calendar/auth-url")
async def calendar_auth_url(user_id: int = Depends(_require_user)):
    state = secrets.token_urlsafe(24)
    _oauth_states[state] = user_id
    return {"url": gcal.auth_url(state)}


@app.get("/calendar/callback")
async def calendar_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    user_id = _oauth_states.pop(state, None) if state else None
    if error or not code or user_id is None:
        return RedirectResponse(f"{FRONTEND_URL}/settings?calendar=error")
    try:
        loop = asyncio.get_event_loop()
        tok = await loop.run_in_executor(None, gcal.exchange_code, code)
        store.save_google_tokens(user_id, tok["access_token"], tok["refresh_token"],
                                 tok["expiry"], gcal.SCOPE)
        return RedirectResponse(f"{FRONTEND_URL}/settings?calendar=connected")
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/settings?calendar=error")


@app.get("/calendar/status")
async def calendar_status(user_id: int = Depends(_require_user)):
    return {"connected": store.get_google_tokens(user_id) is not None}
```
(`RedirectResponse`, `asyncio`, `Depends`, and `FRONTEND_URL` already exist in main.py.)

- [ ] **Step 4: Run to verify it passes + full suite**

Run: `cd backend && python -m pytest tests/test_calendar_api.py -q && python -m pytest -q`
Expected: new tests pass; full suite green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_calendar_api.py
git commit -m "feat: calendar connect/callback/status endpoints"
```

---

## Task 4: Frontend — Connect Google Calendar in Settings

**Files:** Modify `frontend/src/api.ts`, `frontend/src/screens/SettingsScreen.tsx`.

- [ ] **Step 1: API helpers** — in `frontend/src/api.ts` add (auth'd, following the `getSettings` pattern):
```ts
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
```

- [ ] **Step 2: Settings UI** — in `SettingsScreen.tsx`, add a "Google Calendar" section between the default-address block and the error block. Read the existing markup first and match it. On mount, read `?calendar=connected|error` from the URL (via `useNavigate`/`window.location.search`) to show a confirmation, then call `calendarStatus()`. Add a connect button that does `window.location.href = await calendarAuthUrl()`. Sketch:
```tsx
// state
const [calConnected, setCalConnected] = useState<boolean | null>(null)
// effect (after the settings load effect)
useEffect(() => {
  if (!user) return
  calendarStatus().then((s) => setCalConnected(s.connected)).catch(() => setCalConnected(false))
}, [user])
const connectCalendar = async () => { window.location.href = await calendarAuthUrl() }
```
```tsx
<div className="mt-7">
  <p className="mb-2 block text-sm font-medium text-[var(--color-ink)]">Google Calendar</p>
  {calConnected ? (
    <p className="text-sm text-[var(--color-primary)]">Connected — meetups can be added to your calendar.</p>
  ) : (
    <button type="button" onClick={connectCalendar}
      className="cursor-pointer rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-medium text-[var(--color-ink)] hover:bg-[var(--color-surface)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]">
      Connect Google Calendar
    </button>
  )}
</div>
```

- [ ] **Step 3: Verify** — `cd frontend && npm run build` → succeeds.

- [ ] **Step 4: Commit**
```bash
git add frontend/src/api.ts frontend/src/screens/SettingsScreen.tsx
git commit -m "feat: connect google calendar from settings"
```

---

# PHASE 2 — Add to Google Calendar (write-back)

## Task 5: Calendar event endpoint

**Files:** Modify `backend/app/main.py`; extend `backend/tests/test_calendar_api.py`.

- [ ] **Step 1: Add the failing test** (append to `backend/tests/test_calendar_api.py`):
```python
def test_create_event_inserts_and_returns_link():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.gcal.insert_event", return_value={"htmlLink": "https://cal/evt"}) as ins:
            r = client.post("/calendar/event", json={
                "summary": "Pick up iPhone 14", "location": "Marienplatz",
                "start_iso": "2026-06-20T15:00:00+02:00", "end_iso": "2026-06-20T15:30:00+02:00",
            })
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["htmlLink"] == "https://cal/evt"
    args = ins.call_args[0]
    assert args[0] == 4 and args[1] == "Pick up iPhone 14" and args[2] == "Marienplatz"


def test_create_event_409_when_not_connected():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.gcal.insert_event", return_value=None):
            r = client.post("/calendar/event", json={
                "summary": "x", "location": "y",
                "start_iso": "2026-06-20T15:00:00+02:00", "end_iso": "2026-06-20T15:30:00+02:00"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 409
```

- [ ] **Step 2: Run to verify failure** — `cd backend && python -m pytest tests/test_calendar_api.py -k event -v` → 404/fails.

- [ ] **Step 3: Implement** — in `backend/app/main.py` add a request model near the others and the endpoint:
```python
class CalendarEventRequest(BaseModel):
    summary: str
    location: str = ""
    start_iso: str
    end_iso: str


@app.post("/calendar/event")
async def calendar_event(req: CalendarEventRequest, user_id: int = Depends(_require_user)):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, gcal.insert_event, user_id, req.summary, req.location, req.start_iso, req.end_iso)
    if result is None:
        raise HTTPException(status_code=409, detail="Calendar not connected")
    return result
```

- [ ] **Step 4: Run tests** — `cd backend && python -m pytest tests/test_calendar_api.py -q && python -m pytest -q` → all pass.

- [ ] **Step 5: Commit**
```bash
git add backend/app/main.py backend/tests/test_calendar_api.py
git commit -m "feat: add-to-calendar event insert endpoint"
```

---

## Task 6: Frontend — AddToCalendar component on Done + History

**Files:** Modify `frontend/src/api.ts`; Create `frontend/src/components/AddToCalendar.tsx`; Modify `frontend/src/screens/DoneScreen.tsx`, `frontend/src/screens/HistoryScreen.tsx`, and `frontend/src/App.tsx` (pass through props if needed).

- [ ] **Step 1: API helper** — in `api.ts`:
```ts
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
```

- [ ] **Step 2: Create `frontend/src/components/AddToCalendar.tsx`** — a self-contained control: a `datetime-local` input (default tomorrow 15:00) + an "Add to Google Calendar" button; on success shows a link to the event; on `not_connected` shows a "Connect calendar in Settings" hint. Match the dark theme tokens.
```tsx
import { useState } from 'react'
import { addCalendarEvent } from '../api'

function defaultStart(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  d.setHours(15, 0, 0, 0)
  // to value for <input type="datetime-local"> (local, no seconds)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function AddToCalendar({ summary, location }: { summary: string; location: string }) {
  const [when, setWhen] = useState(defaultStart())
  const [busy, setBusy] = useState(false)
  const [link, setLink] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const add = async () => {
    setBusy(true); setErr(null)
    try {
      const start = new Date(when)
      const end = new Date(start.getTime() + 30 * 60 * 1000)
      const res = await addCalendarEvent({
        summary, location,
        start_iso: start.toISOString(), end_iso: end.toISOString(),
      })
      setLink(res.htmlLink)
    } catch (e) {
      setErr((e as Error).message === 'not_connected'
        ? 'Connect Google Calendar in Settings first.' : 'Could not add to calendar.')
    } finally { setBusy(false) }
  }

  if (link) {
    return (
      <a href={link} target="_blank" rel="noreferrer"
        className="inline-flex items-center gap-2 text-sm font-medium text-[var(--color-primary)]">
        ✓ Added — view in Google Calendar
      </a>
    )
  }
  return (
    <div className="flex flex-col gap-2">
      <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)}
        className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-4 py-2.5 text-sm text-[var(--color-ink)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]" />
      <button type="button" onClick={add} disabled={busy}
        className="cursor-pointer rounded-xl bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-medium text-[var(--color-ink)] hover:bg-[var(--color-surface)] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]">
        {busy ? 'Adding…' : 'Add to Google Calendar'}
      </button>
      {err && <p className="text-xs text-[var(--color-ink-muted)]">{err}</p>}
    </div>
  )
}
```

- [ ] **Step 3: Wire into DoneScreen** — in `frontend/src/screens/DoneScreen.tsx`, import the component and render it in the Actions area (after the existing buttons). Build `summary`/`location` from the existing vars (`chosen?.title`, `p?.location`):
```tsx
{(p?.location || chosen?.title) && (
  <div className="mt-4">
    <AddToCalendar summary={chosen?.title ? `Pick up ${chosen.title}` : 'Envoy meetup'} location={p?.location ?? ''} />
  </div>
)}
```

- [ ] **Step 4: Wire into HistoryScreen detail** — in the `selected` branch of `frontend/src/screens/HistoryScreen.tsx`, render `<AddToCalendar summary={`Pick up ${selected.query ?? 'item'}`} location={(selected.meetup as {location?: string}).location ?? ''} />` near the meetup line, only when a location exists.

- [ ] **Step 5: Verify** — `cd frontend && npm run build` → succeeds.

- [ ] **Step 6: Commit**
```bash
git add frontend/src/api.ts frontend/src/components/AddToCalendar.tsx frontend/src/screens/DoneScreen.tsx frontend/src/screens/HistoryScreen.tsx
git commit -m "feat: add-to-google-calendar button on done + history"
```

---

# PHASE 3 — Freebusy + interactive reschedule (heaviest; cut line)

## Task 7: Freebusy endpoint

**Files:** Modify `backend/app/main.py`; extend `backend/tests/test_calendar_api.py`.

- [ ] **Step 1: Failing test** (append):
```python
def test_freebusy_returns_busy_intervals():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.gcal.query_freebusy",
                   return_value=[{"start": "2026-06-20T10:00:00Z", "end": "2026-06-20T11:00:00Z"}]):
            r = client.get("/calendar/freebusy?time_min=2026-06-20T00:00:00Z&time_max=2026-06-27T00:00:00Z")
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["busy"][0]["start"].startswith("2026-06-20")
```

- [ ] **Step 2: Run** → 404/fails.

- [ ] **Step 3: Implement** — in `main.py`:
```python
@app.get("/calendar/freebusy")
async def calendar_freebusy(time_min: str, time_max: str, user_id: int = Depends(_require_user)):
    loop = asyncio.get_event_loop()
    busy = await loop.run_in_executor(None, gcal.query_freebusy, user_id, time_min, time_max)
    return {"busy": busy}
```

- [ ] **Step 4: Run tests** → pass; full suite green.

- [ ] **Step 5: Commit**
```bash
git add backend/app/main.py backend/tests/test_calendar_api.py
git commit -m "feat: freebusy endpoint"
```

---

## Task 8: Graph — structured reschedule + seller time turn

**Files:** Modify `backend/app/agents/coordinate.py`, `backend/app/graph.py`; Test `backend/tests/test_reschedule.py` (new).

Context: `confirm_meetup_node(state)` currently does `choice = interrupt(state["pending_decision"])` and handles `"cancel"`/`"reschedule"`/confirm. `_after_confirm_meetup` routes `plan_meetup` on reschedule, else END. We add: a structured reschedule (`{"action":"reschedule","slots":[...]}`) that asks the seller to pick a slot, then re-confirms.

- [ ] **Step 1: Failing test** — `backend/tests/test_reschedule.py`:
```python
from unittest.mock import patch
from app.agents.coordinate import confirm_meetup_node, seller_time_turn_node
from app.graph import _after_confirm_meetup, _after_seller_time_turn


def _state():
    return {
        "meetup_proposal": {"location": "Marienplatz", "time_suggestion": "Sat afternoon",
                            "final_price": 170, "buyer_route": {"duration_text": "15 min"},
                            "seller_location": "Schwabing"},
        "pending_decision": {"checkpoint": "confirm_meetup", "summary": "", "options": [], "context": {}},
        "decision_history": [], "status": "awaiting_human",
    }


def test_structured_reschedule_routes_to_seller_time():
    st = _state()
    with patch("app.agents.coordinate.interrupt",
               return_value={"action": "reschedule", "slots": ["2026-06-20T15:00:00+02:00"]}):
        out = confirm_meetup_node(st)
    assert out["status"] == "awaiting_seller"
    assert out["pending_decision"]["checkpoint"] == "seller_time"
    assert out["pending_decision"]["context"]["slots"] == ["2026-06-20T15:00:00+02:00"]
    assert _after_confirm_meetup(out) == "seller_time_turn"


def test_seller_time_turn_sets_concrete_time_and_reconfirms():
    st = _state()
    st["pending_decision"] = {"checkpoint": "seller_time", "summary": "", "options": [],
                              "context": {"slots": ["2026-06-20T15:00:00+02:00", "2026-06-21T11:00:00+02:00"]}}
    with patch("app.agents.coordinate.interrupt", return_value="time:1"):
        out = seller_time_turn_node(st)
    assert out["meetup_proposal"]["time_suggestion"] == "2026-06-21T11:00:00+02:00"
    assert out["pending_decision"]["checkpoint"] == "confirm_meetup"
    assert out["status"] == "awaiting_human"
    assert _after_seller_time_turn(out) == "confirm_meetup"
```

- [ ] **Step 2: Run** → ImportError (`seller_time_turn_node`, `_after_seller_time_turn`).

- [ ] **Step 3: Implement**

In `backend/app/agents/coordinate.py`:

(a) At the top of `confirm_meetup_node`, after `choice = interrupt(state["pending_decision"])`, handle the structured reschedule BEFORE the existing string handling:
```python
    if isinstance(choice, dict) and choice.get("action") == "reschedule":
        slots = choice.get("slots") or []
        pending = {
            "checkpoint": "seller_time",
            "summary": f"Buyer proposes {len(slots)} time(s) to meet. Pick one.",
            "options": [{"id": f"time:{i}", "label": s} for i, s in enumerate(slots)],
            "context": {"slots": slots},
        }
        return {
            "pending_decision": pending, "status": "awaiting_seller",
            "decision_history": state["decision_history"]
                + [{"checkpoint": "confirm_meetup", "choice": "reschedule", "ts": _ts()}],
        }
```
Add a `_ts()` helper if coordinate.py lacks one (it imports `datetime`):
```python
def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
```
Keep the rest of `confirm_meetup_node` (the existing `cancel`/`reschedule`/confirm string handling) unchanged below this block.

(b) Add the new node:
```python
def seller_time_turn_node(state: ProcurementState) -> dict:
    """Seller picks one of the buyer's proposed slots (Telegram); re-confirm to buyer."""
    pending = state["pending_decision"]
    slots = pending["context"]["slots"]
    choice = interrupt(pending)            # "time:<index>"
    idx = 0
    if isinstance(choice, str) and choice.startswith("time:"):
        try:
            idx = int(choice.split(":", 1)[1])
        except ValueError:
            idx = 0
    chosen = slots[idx] if 0 <= idx < len(slots) else (slots[0] if slots else None)
    proposal = {**state["meetup_proposal"], "time_suggestion": chosen}
    confirm_pending = {
        "checkpoint": "confirm_meetup",
        "summary": f"Seller agreed to {chosen}. Confirm the meetup?",
        "options": [
            {"id": "confirm", "label": "Confirm meetup"},
            {"id": "reschedule", "label": "Suggest different time"},
            {"id": "cancel", "label": "Cancel"},
        ],
        "context": {"meetup_proposal": proposal},
    }
    return {
        "meetup_proposal": proposal, "pending_decision": confirm_pending,
        "status": "awaiting_human",
        "decision_history": state["decision_history"]
            + [{"checkpoint": "seller_time", "choice": choice, "ts": _ts()}],
    }
```

In `backend/app/graph.py`:

(c) Import `seller_time_turn_node` from coordinate (extend the existing coordinate import).

(d) Replace `_after_confirm_meetup` and add `_after_seller_time_turn`:
```python
def _after_confirm_meetup(state: ProcurementState) -> str:
    if state["status"] == "awaiting_seller":
        return "seller_time_turn"
    if state["status"] == "done":
        return END
    if state["status"] == "failed":
        return END
    return "plan_meetup"  # plain reschedule


def _after_seller_time_turn(state: ProcurementState) -> str:
    return "confirm_meetup"
```

(e) In `build_graph()`: register the node and edges:
```python
    builder.add_node("seller_time_turn", seller_time_turn_node)
```
Replace the existing `confirm_meetup` conditional-edges block with:
```python
    builder.add_conditional_edges(
        "confirm_meetup",
        _after_confirm_meetup,
        {"seller_time_turn": "seller_time_turn", "plan_meetup": "plan_meetup", END: END},
    )
    builder.add_edge("seller_time_turn", "confirm_meetup")
```

- [ ] **Step 4: Run tests** — `cd backend && python -m pytest tests/test_reschedule.py tests/test_api.py -q && python -m pytest -q`
Expected: new tests pass; graph compiles (test_api imports it); full suite green.

- [ ] **Step 5: Commit**
```bash
git add backend/app/agents/coordinate.py backend/app/graph.py backend/tests/test_reschedule.py
git commit -m "feat: structured reschedule + seller time-pick graph node"
```

---

## Task 9: Telegram time notify + propose-times endpoint

**Files:** Modify `backend/app/telegram.py`, `backend/app/main.py`; Test `backend/tests/test_reschedule.py` (extend).

- [ ] **Step 1: Failing tests** (append to `backend/tests/test_reschedule.py`):
```python
def test_build_seller_time_message_lists_slots():
    import app.telegram as tg
    pending = {"summary": "Buyer proposes 2 time(s) to meet. Pick one.",
               "context": {"slots": ["2026-06-20T15:00:00+02:00", "2026-06-21T11:00:00+02:00"]}}
    text, buttons = tg.build_seller_time_message(pending)
    cbs = [cb for _, cb in buttons]
    assert cbs == ["time:0", "time:1"]


def test_dispatch_routes_time_callback(monkeypatch):
    import importlib, app.store as store, app.telegram as tg
    import tempfile, os
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.environ["ENVOY_DB"] = p
    importlib.reload(store); store.init_store(); importlib.reload(tg)
    store.register_chat(55, "seller"); store.attach_session(55, "sess-T")
    captured = {}
    async def on_reply(sid, choice): captured.update(sid=sid, choice=choice)
    import asyncio
    upd = {"callback_query": {"data": "time:1", "message": {"chat": {"id": 55}}}}
    asyncio.get_event_loop().run_until_complete(tg._dispatch(upd, on_reply))
    assert captured == {"sid": "sess-T", "choice": "time:1"}
```

- [ ] **Step 2: Run** → fails (`build_seller_time_message` missing; `time:` not routed).

- [ ] **Step 3: Implement**

In `backend/app/telegram.py`:
(a) Add the message builder + notifier (mirrors `build_seller_message`/`notify_seller`):
```python
def build_seller_time_message(pending: dict) -> tuple[str, list[tuple[str, str]]]:
    slots = pending["context"]["slots"]
    text = pending["summary"] + "\n\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(slots))
    buttons = [(f"{i+1}. {s}", f"time:{i}") for i, s in enumerate(slots)]
    return text, buttons


def notify_seller_time(session_id: str, pending: dict) -> None:
    chat_id = store.chat_for_role("seller")
    if chat_id is None:
        return
    store.attach_session(chat_id, session_id)
    text, buttons = build_seller_time_message(pending)
    tg_send(chat_id, text, buttons)
```
(b) In `_dispatch`, broaden the callback guard so both `seller:` and `time:` route to `on_seller_reply`. Change the condition `if cb and cb.get("data", "").startswith("seller:"):` to:
```python
    if cb and (cb.get("data", "").startswith("seller:") or cb.get("data", "").startswith("time:")):
        chat_id = cb["message"]["chat"]["id"]
        link = store.resolve_chat(chat_id)
        if not link or not link.get("session_id"):
            return
        data = cb["data"]
        choice = data.split(":", 1)[1] if data.startswith("seller:") else data  # keep "time:N" intact
        await on_seller_reply(link["session_id"], choice)
        return
```
(Seller-turn callbacks still resume with `accept`/`counter`/`reject`; time callbacks resume with the full `time:N` string, which `seller_time_turn_node` parses.)

In `backend/app/main.py`:
(c) In `_on_state_committed`, extend the seller-notify branch to handle the `seller_time` checkpoint. Replace the `if status == "awaiting_seller" and ...checkpoint == "seller_turn":` block with:
```python
    if status == "awaiting_seller":
        cp = state.get("pending_decision", {}).get("checkpoint")
        if cp == "seller_turn":
            notify_seller(session_id, state["pending_decision"])
        elif cp == "seller_time":
            notify_seller_time(session_id, state["pending_decision"])
```
Add `notify_seller_time` to the telegram import: `from app.telegram import notify_seller, notify_seller_time, notify_buyer, poll_updates`.
(d) Also update the `_run_graph` bridge so the `seller_time` checkpoint keeps `awaiting_seller`. The current bridge sets `awaiting_seller` only for `checkpoint == "seller_turn"`. Change that condition to:
```python
        state["status"] = ("awaiting_seller"
                           if isinstance(pending, dict) and pending.get("checkpoint") in ("seller_turn", "seller_time")
                           else "awaiting_human")
```
(e) Add the propose-times endpoint (resumes the confirm_meetup interrupt with a structured payload):
```python
class ProposeTimesRequest(BaseModel):
    slots: list[str]


@app.post("/session/{session_id}/propose-times")
async def propose_times(session_id: str, req: ProposeTimesRequest):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    thread_id = _sessions[session_id]["thread_id"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _run_graph, thread_id,
        Command(resume={"action": "reschedule", "slots": req.slots}), session_id)
    return {"ok": True}
```

- [ ] **Step 4: Run tests** — `cd backend && python -m pytest tests/test_reschedule.py -q && python -m pytest -q` → all pass.

- [ ] **Step 5: Commit**
```bash
git add backend/app/telegram.py backend/app/main.py backend/tests/test_reschedule.py
git commit -m "feat: telegram time-pick + propose-times resume"
```

---

## Task 10: Frontend — WeekPicker + interactive reschedule

**Files:** Modify `frontend/src/api.ts`; Create `frontend/src/components/WeekPicker.tsx`; Modify `frontend/src/screens/MeetupScreen.tsx`, `frontend/src/App.tsx` (thread a `sessionId` to MeetupScreen).

- [ ] **Step 1: API helpers** — in `api.ts`:
```ts
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
```

- [ ] **Step 2: Create `frontend/src/components/WeekPicker.tsx`** — a 7-day × 3-slot (morning 10:00 / afternoon 15:00 / evening 18:00) grid for the next 7 days. Fetch freebusy for the window on mount; grey out + disable any slot overlapping a busy interval. Let the buyer toggle up to 3 slots; "Send to seller" calls back with the selected ISO datetimes.
```tsx
import { useEffect, useState } from 'react'
import { getFreebusy } from '../api'

const SLOTS = [{ label: 'Morning', h: 10 }, { label: 'Afternoon', h: 15 }, { label: 'Evening', h: 18 }]

function isBusy(d: Date, busy: { start: string; end: string }[]): boolean {
  const t = d.getTime()
  return busy.some((b) => t >= new Date(b.start).getTime() && t < new Date(b.end).getTime())
}

export default function WeekPicker({ onSend, onCancel }: { onSend: (slots: string[]) => void; onCancel: () => void }) {
  const [busy, setBusy] = useState<{ start: string; end: string }[]>([])
  const [picked, setPicked] = useState<string[]>([])
  const days = Array.from({ length: 7 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i + 1); return d })

  useEffect(() => {
    const from = new Date(); from.setHours(0, 0, 0, 0)
    const to = new Date(from); to.setDate(to.getDate() + 8)
    getFreebusy(from.toISOString(), to.toISOString()).then((r) => setBusy(r.busy)).catch(() => {})
  }, [])

  const toggle = (iso: string) => setPicked((p) =>
    p.includes(iso) ? p.filter((x) => x !== iso) : (p.length < 3 ? [...p, iso] : p))

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <p className="mb-3 text-sm font-medium text-[var(--color-ink)]">Pick up to 3 times you're free</p>
      <div className="space-y-2">
        {days.map((day) => (
          <div key={day.toDateString()} className="flex items-center gap-2">
            <span className="w-10 shrink-0 text-xs text-[var(--color-ink-muted)]">
              {day.toLocaleDateString(undefined, { weekday: 'short' })}
            </span>
            {SLOTS.map((s) => {
              const d = new Date(day); d.setHours(s.h, 0, 0, 0)
              const iso = d.toISOString()
              const disabled = isBusy(d, busy)
              const on = picked.includes(iso)
              return (
                <button key={s.h} type="button" disabled={disabled} onClick={() => toggle(iso)}
                  className={[
                    'flex-1 rounded-lg px-2 py-2 text-xs font-medium',
                    disabled ? 'cursor-not-allowed bg-[var(--color-bg)] text-[var(--color-ink-faint)] line-through'
                      : on ? 'bg-[var(--color-primary)] text-[var(--color-primary-text)]'
                      : 'bg-[var(--color-surface-raised)] text-[var(--color-ink)] hover:brightness-110',
                  ].join(' ')}>
                  {s.label}
                </button>
              )
            })}
          </div>
        ))}
      </div>
      <div className="mt-4 flex gap-2">
        <button type="button" disabled={!picked.length} onClick={() => onSend(picked)}
          className="flex-1 rounded-xl bg-[var(--color-primary)] py-3 text-sm font-semibold text-[var(--color-primary-text)] disabled:opacity-40">
          Send {picked.length || ''} to seller
        </button>
        <button type="button" onClick={onCancel}
          className="rounded-xl bg-[var(--color-surface-raised)] px-5 py-3 text-sm text-[var(--color-ink)]">Cancel</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Thread `sessionId` to MeetupScreen** — in `frontend/src/App.tsx`, the `BuyerFlow` already holds `sessionId`. Change the meetup branch to `return <MeetupScreen state={state} onFeedback={sendFeedback} sessionId={sessionId} />`. In `MeetupScreen.tsx`, add `sessionId: string` to `Props`.

- [ ] **Step 4: Intercept "reschedule" in MeetupScreen** — in `MeetupScreen.tsx`, instead of letting the `reschedule` option call `onFeedback('reschedule')`, open the WeekPicker. Add `const [picking, setPicking] = useState(false)` and a wrapper passed to `CheckpointBanner` that intercepts the reschedule id:
```tsx
import WeekPicker from '../components/WeekPicker'
import { proposeTimes } from '../api'
// ...
const handleChoice = async (choice: string) => {
  if (choice === 'reschedule') { setPicking(true); return }
  setLoading(true)
  await onFeedback(choice)
}
// render: when picking, show the WeekPicker instead of (or above) the banner
{picking ? (
  <WeekPicker
    onCancel={() => setPicking(false)}
    onSend={async (slots) => { setPicking(false); setLoading(true); await proposeTimes(sessionId, slots) }}
  />
) : (
  <CheckpointBanner decision={decision} onChoice={handleChoice} loading={loading} eyebrow="Final step" />
)}
```
After `proposeTimes`, the session goes to `awaiting_seller`; the existing WebSocket + `awaiting_seller` ProcessingScreen show "Waiting for the seller…" until the seller picks a slot and the buyer is returned to a fresh confirm_meetup. (Confirm `CheckpointBanner`'s prop name is `onChoice`; adjust if the real component differs — read it first.)

- [ ] **Step 5: Verify** — `cd frontend && npm run build` → succeeds.

- [ ] **Step 6: Manual check** — with `LIVE_SELLER=true` + Telegram + a connected calendar: reach the meetup checkpoint → "Suggest different time" → busy slots are greyed → pick 2 → "Waiting for seller" → seller taps a slot on Telegram → buyer sees the concrete time on a fresh confirm → confirm → Done → "Add to Google Calendar" creates the event.

- [ ] **Step 7: Commit**
```bash
git add frontend/src/api.ts frontend/src/components/WeekPicker.tsx frontend/src/screens/MeetupScreen.tsx frontend/src/App.tsx
git commit -m "feat: interactive week-picker reschedule"
```

---

## Final verification

- [ ] `cd backend && python -m pytest -q` → all pass.
- [ ] `cd frontend && npm run build` → succeeds.
- [ ] Phase 1: Settings → Connect Google Calendar → consent → returns "Connected".
- [ ] Phase 2: Done/History → datetime picker → Add to Google Calendar → event link works.
- [ ] Phase 3: meetup → Suggest different time → week picker (busy greyed) → seller picks on Telegram → buyer confirms concrete time.

## Spec coverage check

- Build item 4 (calendar onboarding; avoid busy times) → Tasks 1–4 (connection) + Task 7 (freebusy) + Task 10 (busy slots greyed in the picker).
- Build item 5 (interactive two-sided reschedule) → Tasks 8–10.
- New write-back ("add event back to Google Calendar, button on history") → Tasks 5–6 (Done + History detail).
