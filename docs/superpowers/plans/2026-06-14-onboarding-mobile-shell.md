# Onboarding + Mobile App Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a skippable new-user onboarding wizard (Telegram + optional Google Calendar) and a persistent 3-tab bottom navigation (Search / Deal / Me) to Envoy.

**Architecture:** Backend gains per-user Telegram binding via a deep-link token, a `users.onboarded` flag, and two small endpoints. Frontend introduces a layout route (`AppShell`) that renders a persistent `BottomNav` + `<Outlet/>`, moves the existing screens into `/search`, `/deals`, `/me`, and adds a full-screen `/onboarding` wizard gated by the onboarded flag.

**Tech Stack:** Backend — Python, FastAPI, sqlite3 (stdlib), pytest + `fastapi.testclient`. Frontend — React 19, Vite, TypeScript, react-router-dom 7, Tailwind CSS 4. (No frontend test runner exists, so frontend tasks verify via `npm run build` and explicit manual checks.)

**Spec:** `docs/superpowers/specs/2026-06-14-onboarding-mobile-shell-design.md`

---

## File Structure

**Backend (modify):**
- `backend/app/auth.py` — add `onboarded` column, expose it in `_public_user`, add `set_onboarded`.
- `backend/app/telegram.py` — link-token mint/resolve, `/start <token>` binding, per-user `notify_buyer`.
- `backend/app/store.py` — add `chat_for_user`.
- `backend/app/main.py` — endpoints: `POST /onboarding/complete`, `POST /telegram/link-token`, `GET /telegram/status`; pass `user_id` into `notify_buyer`.

**Backend (create tests):**
- `backend/tests/test_onboarding.py`, `backend/tests/test_telegram_link.py`

**Frontend (create):**
- `frontend/src/api.ts` additions (no new file)
- `frontend/src/components/BottomNav.tsx`
- `frontend/src/screens/AppShell.tsx`
- `frontend/src/screens/OnboardingWizard.tsx`

**Frontend (modify):**
- `frontend/src/App.tsx` — restructure routes, add onboarding gate.
- `frontend/src/screens/InputScreen.tsx` — drop the header history/settings icon buttons (now in the tab bar).
- `frontend/src/screens/SettingsScreen.tsx` — used as the Me tab; drop the standalone back button, add a Telegram connect/status row.
- `frontend/src/screens/HistoryScreen.tsx` — used as the Deals tab; drop the standalone back button.
- `frontend/src/api.ts` — `AuthUser.onboarded`, new functions.

---

## Task 1: `onboarded` flag on users

**Files:**
- Modify: `backend/app/auth.py`
- Test: `backend/tests/test_onboarding.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_onboarding.py
import os, tempfile, importlib
import pytest


@pytest.fixture()
def client(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("ENVOY_DB", tmp.name)
    import app.auth as auth
    importlib.reload(auth)
    auth.init_db()
    import app.store as store
    importlib.reload(store)
    store.init_store()
    import app.main as main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    yield TestClient(main.app)
    os.unlink(tmp.name)


def test_new_user_starts_not_onboarded(client):
    body = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()
    assert body["user"]["onboarded"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_onboarding.py::test_new_user_starts_not_onboarded -v`
Expected: FAIL — `KeyError: 'onboarded'` (field not in user payload).

- [ ] **Step 3: Add the column, migration, accessor, and expose the flag**

In `backend/app/auth.py`, inside `init_db()` after the `CREATE TABLE` statement, add a migration mirroring the existing pattern in `store.init_store`:

```python
def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                pw_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'en',
                default_address TEXT NOT NULL DEFAULT '',
                onboarded INTEGER NOT NULL DEFAULT 0
            )"""
        )
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "onboarded" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN onboarded INTEGER NOT NULL DEFAULT 0")
```

Update `_public_user` to select and cast the flag to a bool:

```python
def _public_user(user_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, name, language, default_address, onboarded FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return {}
    u = dict(row)
    u["onboarded"] = bool(u["onboarded"])
    return u
```

Add a setter at the end of the file:

```python
def set_onboarded(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE users SET onboarded = 1 WHERE id = ?", (user_id,))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_onboarding.py::test_new_user_starts_not_onboarded -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth.py backend/tests/test_onboarding.py
git commit -m "feat(backend): add users.onboarded flag exposed on auth payload"
```

---

## Task 2: `POST /onboarding/complete` endpoint

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_onboarding.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_onboarding.py`:

```python
def test_complete_onboarding_flips_flag(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post("/onboarding/complete", headers=h)
    assert r.status_code == 200
    assert r.json()["onboarded"] is True
    assert client.get("/auth/me", headers=h).json()["onboarded"] is True


def test_complete_onboarding_requires_auth(client):
    assert client.post("/onboarding/complete").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_onboarding.py -v`
Expected: FAIL — 404 on `/onboarding/complete` (route not defined).

- [ ] **Step 3: Add the endpoint**

In `backend/app/main.py`, update the auth import to include `set_onboarded`:

```python
from app.auth import (
    init_db, signup, login, user_id_for_token, get_settings, update_settings, AuthError,
    find_or_create_google_user, public_user_for_token, set_onboarded,
)
```

Add the endpoint after `write_settings` (near line 338):

```python
@app.post("/onboarding/complete")
async def complete_onboarding(user_id: int = Depends(_require_user)):
    from app.auth import _public_user
    set_onboarded(user_id)
    return _public_user(user_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_onboarding.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_onboarding.py
git commit -m "feat(backend): POST /onboarding/complete sets onboarded flag"
```

---

## Task 3: Telegram link-token mint/resolve + endpoint

**Files:**
- Modify: `backend/app/telegram.py`, `backend/app/main.py`
- Test: `backend/tests/test_telegram_link.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_telegram_link.py
import os, tempfile, importlib
from unittest.mock import patch
import pytest


@pytest.fixture()
def client(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("ENVOY_DB", tmp.name)
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "EnvoyTestBot")
    import app.auth as auth; importlib.reload(auth); auth.init_db()
    import app.store as store; importlib.reload(store); store.init_store()
    import app.telegram as tg; importlib.reload(tg)
    import app.main as main; importlib.reload(main)
    from fastapi.testclient import TestClient
    yield TestClient(main.app)
    os.unlink(tmp.name)


def test_link_token_returns_deep_link(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    r = client.post("/telegram/link-token", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith("https://t.me/EnvoyTestBot?start=")
    assert body["token"]


def test_link_token_resolves_to_user(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    token = client.post("/telegram/link-token", headers={"Authorization": f"Bearer {tok}"}).json()["token"]
    import app.telegram as tg
    uid = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["id"]
    assert tg.resolve_link_token(token) == uid


def test_link_token_requires_auth(client):
    assert client.post("/telegram/link-token").status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_telegram_link.py -v`
Expected: FAIL — `resolve_link_token` missing / 404 on endpoint.

- [ ] **Step 3: Add mint/resolve to telegram.py**

In `backend/app/telegram.py`, add near the top (after the imports/logger):

```python
import secrets

BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")
# token -> user_id (in-memory; resets on restart, fine for the hackathon)
_LINK_TOKENS: dict[str, int] = {}


def mint_link_token(user_id: int) -> dict:
    """Create a one-use-ish binding token and the Telegram deep link for it."""
    token = secrets.token_urlsafe(16)
    _LINK_TOKENS[token] = user_id
    username = os.environ.get("TELEGRAM_BOT_USERNAME", BOT_USERNAME)
    url = f"https://t.me/{username}?start={token}" if username else ""
    return {"token": token, "url": url}


def resolve_link_token(token: str) -> int | None:
    return _LINK_TOKENS.get(token)
```

> Note: `BOT_USERNAME` is read at import time; the function re-reads the env so tests that set it after import still work.

- [ ] **Step 4: Add the endpoint in main.py**

Add `mint_link_token` to the telegram import in `backend/app/main.py`:

```python
from app.telegram import notify_seller, notify_seller_time, notify_buyer, poll_updates, mint_link_token
```

Add the endpoint after `complete_onboarding`:

```python
@app.post("/telegram/link-token")
async def telegram_link_token(user_id: int = Depends(_require_user)):
    return mint_link_token(user_id)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_telegram_link.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/telegram.py backend/app/main.py backend/tests/test_telegram_link.py
git commit -m "feat(backend): mint per-user Telegram link tokens + endpoint"
```

---

## Task 4: `/start <token>` binds chat to the user

**Files:**
- Modify: `backend/app/telegram.py`
- Test: `backend/tests/test_telegram_link.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_telegram_link.py`:

```python
@pytest.mark.asyncio
async def test_start_with_token_binds_chat_to_user():
    import app.telegram as tg
    import app.store as store
    uid = 77
    token = tg.mint_link_token(uid)["token"]
    upd = {"message": {"chat": {"id": 9001}, "text": f"/start {token}"}}
    with patch("app.telegram.tg_send"):
        await tg._dispatch(upd, on_seller_reply=lambda *a: None)
    assert store.resolve_chat(9001)["user_id"] == uid
    assert store.resolve_chat(9001)["role"] == "buyer"


@pytest.mark.asyncio
async def test_start_seller_still_role_based():
    import app.telegram as tg
    import app.store as store
    upd = {"message": {"chat": {"id": 9002}, "text": "/start seller"}}
    with patch("app.telegram.tg_send"):
        await tg._dispatch(upd, on_seller_reply=lambda *a: None)
    assert store.resolve_chat(9002)["role"] == "seller"
```

This test needs the store table to exist. Add a module-level fixture at the top of the file (after imports):

```python
@pytest.fixture(autouse=True)
def _store_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("ENVOY_DB", tmp.name)
    import app.store as store; importlib.reload(store); store.init_store()
    yield
    os.unlink(tmp.name)
```

> Note: `pytest-asyncio` is already a dependency. If `@pytest.mark.asyncio` is not auto-detected, ensure `asyncio_mode = "auto"` is in `pyproject.toml` (check `[tool.pytest.ini_options]`); if absent, the explicit marker handles it.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_telegram_link.py -k start -v`
Expected: FAIL — `/start <token>` registers role `"buyer"` but `user_id` is `None` (current handler ignores tokens).

- [ ] **Step 3: Update the `/start` handler**

In `backend/app/telegram.py`, replace the `/start` branch inside `_dispatch`:

```python
    # /start <token-or-role> registration
    msg = upd.get("message")
    if msg and msg.get("text", "").startswith("/start"):
        chat_id = msg["chat"]["id"]
        parts = msg["text"].split()
        arg = parts[1] if len(parts) > 1 else "buyer"
        user_id = resolve_link_token(arg)
        if user_id is not None:
            store.register_chat(chat_id, "buyer", user_id)
            tg_send(chat_id, "✅ Connected! You'll get buyer updates here.")
        else:
            role = arg if arg in ("buyer", "seller") else "buyer"
            store.register_chat(chat_id, role)
            tg_send(chat_id, f"Registered as {role}. You'll get negotiation updates here.")
        return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_telegram_link.py -v`
Expected: PASS (all tests in file).

- [ ] **Step 5: Commit**

```bash
git add backend/app/telegram.py backend/tests/test_telegram_link.py
git commit -m "feat(backend): bind Telegram chat to user via /start token"
```

---

## Task 5: Per-user `notify_buyer` routing + `chat_for_user`

**Files:**
- Modify: `backend/app/store.py`, `backend/app/telegram.py`, `backend/app/main.py`
- Test: `backend/tests/test_telegram_link.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_telegram_link.py`:

```python
def test_chat_for_user_returns_bound_chat():
    import app.store as store
    store.register_chat(5005, "buyer", user_id=42)
    assert store.chat_for_user(42) == 5005
    assert store.chat_for_user(999) is None


def test_notify_buyer_routes_to_user_chat(monkeypatch):
    import app.telegram as tg
    import app.store as store
    store.register_chat(6006, "buyer", user_id=42)
    sent = {}
    monkeypatch.setattr(tg, "tg_send", lambda chat_id, text, buttons=None: sent.update(chat_id=chat_id, text=text))
    tg.notify_buyer("sess-1", "Seller replied — review", user_id=42)
    assert sent["chat_id"] == 6006


def test_notify_buyer_falls_back_to_role(monkeypatch):
    import app.telegram as tg
    import app.store as store
    store.register_chat(7007, "buyer")  # no user_id
    sent = {}
    monkeypatch.setattr(tg, "tg_send", lambda chat_id, text, buttons=None: sent.update(chat_id=chat_id))
    tg.notify_buyer("sess-2", "msg", user_id=None)
    assert sent["chat_id"] == 7007
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_telegram_link.py -k "chat_for_user or notify_buyer" -v`
Expected: FAIL — `chat_for_user` missing; `notify_buyer` has no `user_id` parameter.

- [ ] **Step 3: Add `chat_for_user` to store.py**

In `backend/app/store.py`, add after `chat_for_role`:

```python
def chat_for_user(user_id: int) -> int | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT chat_id FROM telegram_links WHERE user_id=? AND role='buyer' "
            "ORDER BY rowid DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return row["chat_id"] if row else None
```

- [ ] **Step 4: Update `notify_buyer`**

In `backend/app/telegram.py`, replace `notify_buyer`:

```python
def notify_buyer(session_id: str, message: str, user_id: int | None = None) -> None:
    chat_id = store.chat_for_user(user_id) if user_id is not None else None
    if chat_id is None:
        chat_id = store.chat_for_role("buyer")  # demo fallback
    if chat_id is None:
        return
    tg_send(chat_id, f"{message}\n\n{FRONTEND_URL}/?session={session_id}")
```

- [ ] **Step 5: Pass `user_id` at the call site**

In `backend/app/main.py`, in `_on_state_committed`, update the `notify_buyer` call (around line 107):

```python
            notify_buyer(
                session_id,
                f"Seller {verb} — review ▸",
                user_id=_sessions.get(session_id, {}).get("user_id"),
            )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_telegram_link.py -v`
Expected: PASS.

- [ ] **Step 7: Run the full backend suite (no regressions)**

Run: `cd backend && python -m pytest -q`
Expected: PASS (existing tests, e.g. `test_telegram.py`, still green).

- [ ] **Step 8: Commit**

```bash
git add backend/app/store.py backend/app/telegram.py backend/app/main.py backend/tests/test_telegram_link.py
git commit -m "feat(backend): route buyer notifications to the session owner's chat"
```

---

## Task 6: `GET /telegram/status`

**Files:**
- Modify: `backend/app/store.py`, `backend/app/main.py`
- Test: `backend/tests/test_telegram_link.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_telegram_link.py`:

```python
def test_telegram_status_reflects_binding(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/telegram/status", headers=h).json()["connected"] is False
    uid = client.get("/auth/me", headers=h).json()["id"]
    import app.store as store
    store.register_chat(8008, "buyer", user_id=uid)
    assert client.get("/telegram/status", headers=h).json()["connected"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_telegram_link.py::test_telegram_status_reflects_binding -v`
Expected: FAIL — 404 (route not defined).

- [ ] **Step 3: Add the endpoint**

In `backend/app/main.py`, after `telegram_link_token`:

```python
@app.get("/telegram/status")
async def telegram_status(user_id: int = Depends(_require_user)):
    return {"connected": store.chat_for_user(user_id) is not None}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_telegram_link.py::test_telegram_status_reflects_binding -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_telegram_link.py
git commit -m "feat(backend): GET /telegram/status for binding state"
```

---

## Task 7: Frontend API client additions

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Add the `onboarded` field to `AuthUser`**

In `frontend/src/api.ts`, update the interface (line 11):

```typescript
export interface AuthUser { id: number; email: string; name: string; language: string; default_address: string; onboarded: boolean }
```

- [ ] **Step 2: Add the new API functions**

Append to `frontend/src/api.ts`:

```typescript
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
```

- [ ] **Step 3: Verify it type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend): API client for onboarding + telegram binding"
```

---

## Task 8: `BottomNav` component

**Files:**
- Create: `frontend/src/components/BottomNav.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/BottomNav.tsx
import { NavLink } from 'react-router-dom'

const TABS = [
  {
    to: '/search', label: 'Search',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
      </svg>
    ),
  },
  {
    to: '/deals', label: 'Deal',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M11 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5" />
        <path d="m9 12 2 2 9-9-2-2-9 9z" />
      </svg>
    ),
  },
  {
    to: '/me', label: 'Me',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <circle cx="12" cy="8" r="4" /><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1" />
      </svg>
    ),
  },
]

export default function BottomNav() {
  return (
    <nav className="sticky bottom-0 z-20 flex border-t border-[var(--color-border)] bg-[var(--color-bg)]/95 backdrop-blur supports-[backdrop-filter]:bg-[var(--color-bg)]/80 pb-[env(safe-area-inset-bottom)]">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            `flex flex-1 flex-col items-center gap-1 py-2.5 text-[0.6875rem] font-medium transition-colors ${
              isActive ? 'text-[var(--color-primary)]' : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
            }`
          }
        >
          {tab.icon}
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
```

- [ ] **Step 2: Verify it type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/BottomNav.tsx
git commit -m "feat(frontend): BottomNav tab bar (Search/Deal/Me)"
```

---

## Task 9: `AppShell` layout + route restructure + onboarding gate

**Files:**
- Create: `frontend/src/screens/AppShell.tsx`
- Modify: `frontend/src/App.tsx`

This task changes routing structure. `BuyerFlow` (the existing function in `App.tsx`) is kept as-is and reused as the Search tab content.

- [ ] **Step 1: Create `AppShell`**

```tsx
// frontend/src/screens/AppShell.tsx
import { Outlet } from 'react-router-dom'
import BottomNav from '../components/BottomNav'

export default function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col bg-[var(--color-bg)]">
      <div className="flex-1">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  )
}
```

- [ ] **Step 2: Rewrite `App.tsx` routes**

Replace the body of `frontend/src/App.tsx`'s `App` component (the `export default function App`) and keep `BuyerFlow` unchanged. New `App`:

```tsx
import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import InputScreen from './screens/InputScreen'
import ProcessingScreen from './screens/ProcessingScreen'
import ChooseScreen from './screens/ChooseScreen'
import NegotiateScreen from './screens/NegotiateScreen'
import MeetupScreen from './screens/MeetupScreen'
import DoneScreen from './screens/DoneScreen'
import AgentView from './admin/AgentView'
import AuthScreen from './screens/AuthScreen'
import SettingsScreen from './screens/SettingsScreen'
import HistoryScreen from './screens/HistoryScreen'
import AppShell from './screens/AppShell'
import OnboardingWizard from './screens/OnboardingWizard'
import { useSession } from './useSession'
import { useAuth } from './auth/AuthProvider'

// BuyerFlow stays exactly as it is today (search → … → done) — used as the Search tab.
function BuyerFlow() {
  const { user } = useAuth()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const { state, sendFeedback } = useSession(sessionId)

  if (!user) return <AuthScreen />
  if (!sessionId) return <InputScreen onStart={setSessionId} />

  const status = state?.status
  if (!status || status === 'searching' || status === 'reviewing') {
    return <ProcessingScreen status={status} />
  }
  if (status === 'awaiting_human') {
    const cp = state?.pending_decision?.checkpoint
    if (cp === 'confirm_candidate') return <ChooseScreen state={state} onFeedback={sendFeedback} />
    if (cp === 'confirm_offer') return <NegotiateScreen state={state} onFeedback={sendFeedback} />
    if (cp === 'confirm_meetup') return <MeetupScreen state={state} onFeedback={sendFeedback} sessionId={sessionId!} />
  }
  if (status === 'awaiting_seller') return <ProcessingScreen status={status} />
  if (status === 'negotiating' || status === 'coordinating') return <ProcessingScreen status={status} />
  if (status === 'done') return <DoneScreen state={state} sessionId={sessionId!} />
  return <ProcessingScreen status={status} />
}

// Redirects authenticated-but-not-onboarded users into the wizard.
function OnboardingGate() {
  const { user } = useAuth()
  const navigate = useNavigate()
  useEffect(() => {
    if (user && !user.onboarded) navigate('/onboarding', { replace: true })
  }, [user, navigate])
  return null
}

export default function App() {
  const { user } = useAuth()
  if (!user) return <AuthScreen />

  return (
    <>
      <OnboardingGate />
      <Routes>
        <Route path="/onboarding" element={<OnboardingWizard />} />
        <Route element={<AppShell />}>
          <Route path="/search" element={<BuyerFlow />} />
          <Route path="/deals" element={<HistoryScreen />} />
          <Route path="/me" element={<SettingsScreen />} />
        </Route>
        <Route path="/admin" element={<AgentView />} />
        {/* legacy redirects */}
        <Route path="/" element={<Navigate to="/search" replace />} />
        <Route path="/history" element={<Navigate to="/deals" replace />} />
        <Route path="/settings" element={<Navigate to="/me" replace />} />
        <Route path="*" element={<Navigate to="/search" replace />} />
      </Routes>
    </>
  )
}
```

> Note: `BuyerFlow` already guards `!user`, but the top-level gate makes auth explicit and lets `OnboardingGate` run. The existing `?session=` and `?token=` URL params are handled by `AuthProvider`/`useSession` and are unaffected by the redirect because they read `window.location` before navigation; the `?token=` Google return lands on `/` → redirects to `/search`.

- [ ] **Step 3: Verify build + type-check**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Build succeeds.

- [ ] **Step 4: Manual check**

Run `npm run dev`, log in as an existing (already-onboarded) user. Verify: landing on `/` redirects to `/search`; the bottom tab bar is visible; tapping Deal → `/deals`, Me → `/me`; `/history` and `/settings` redirect.
Expected: All tabs reachable, nav highlights the active tab.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/screens/AppShell.tsx frontend/src/App.tsx
git commit -m "feat(frontend): AppShell layout, tab routes, onboarding gate"
```

---

## Task 10: `OnboardingWizard`

**Files:**
- Create: `frontend/src/screens/OnboardingWizard.tsx`

The wizard has 3 steps: Welcome → Telegram → Calendar. It polls `telegramStatus` while on the Telegram step. Completing/skipping calls `completeOnboarding()` (and refreshes the auth user so the gate stops firing) then navigates to `/search`. The Calendar "Connect" first completes onboarding, then redirects to the existing calendar OAuth (returns to `/me`).

- [ ] **Step 1: Add a `refreshUser` to AuthProvider**

The wizard must update `user.onboarded` locally after completing, or the `OnboardingGate` will bounce it back. Add a `refreshUser` to `frontend/src/auth/AuthProvider.tsx`.

In the `AuthValue` interface add:

```typescript
  refreshUser: () => Promise<void>
```

Add the implementation inside `AuthProvider` (after `loginWithToken`):

```typescript
  const refreshUser = useCallback(async () => {
    const u = await fetchMe()
    setUser(u)
    const raw = localStorage.getItem(KEY)
    if (raw) {
      try {
        const parsed = JSON.parse(raw)
        localStorage.setItem(KEY, JSON.stringify({ ...parsed, user: u }))
      } catch { /* ignore */ }
    }
  }, [])
```

Add `refreshUser` to the context value:

```tsx
  return <AuthContext.Provider value={{ user, token, login, signup, loginWithToken, logout, refreshUser }}>{children}</AuthContext.Provider>
```

- [ ] **Step 2: Create the wizard**

```tsx
// frontend/src/screens/OnboardingWizard.tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import {
  completeOnboarding, telegramLinkToken, telegramStatus, calendarAuthUrl,
} from '../api'

export default function OnboardingWizard() {
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const [step, setStep] = useState(0) // 0 welcome, 1 telegram, 2 calendar
  const [tgUrl, setTgUrl] = useState<string | null>(null)
  const [tgConnected, setTgConnected] = useState(false)

  // Fetch the deep link when entering the Telegram step.
  useEffect(() => {
    if (step !== 1 || tgUrl) return
    telegramLinkToken().then((r) => setTgUrl(r.url)).catch(() => setTgUrl(''))
  }, [step, tgUrl])

  // Poll binding status while on the Telegram step.
  useEffect(() => {
    if (step !== 1 || tgConnected) return
    const id = setInterval(() => {
      telegramStatus().then((s) => { if (s.connected) setTgConnected(true) }).catch(() => {})
    }, 2500)
    return () => clearInterval(id)
  }, [step, tgConnected])

  const finish = async () => {
    try { await completeOnboarding(); await refreshUser() } catch { /* ignore */ }
    navigate('/search', { replace: true })
  }

  const connectCalendar = async () => {
    try { await completeOnboarding(); await refreshUser() } catch { /* ignore */ }
    window.location.href = await calendarAuthUrl()
  }

  const Dots = () => (
    <div className="flex gap-1.5">
      {[0, 1, 2].map((i) => (
        <span key={i} className={`h-1 w-6 rounded-full ${i <= step ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-border)]'}`} />
      ))}
    </div>
  )

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[var(--color-bg)] px-5 py-10 sm:px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 opacity-70"
        style={{ background: 'radial-gradient(60% 120% at 50% 0%, oklch(0.62 0.165 150 / 0.16), transparent 70%)' }}
      />
      <div className="console-rise relative mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-[26rem] flex-col">
        <header className="flex items-center justify-between">
          <Dots />
          {step > 0 && (
            <button type="button" onClick={finish}
              className="cursor-pointer text-sm font-medium text-[var(--color-ink-muted)] transition-colors hover:text-[var(--color-ink)]">
              Skip
            </button>
          )}
        </header>

        <div className="flex flex-1 flex-col justify-center">
          {step === 0 && (
            <>
              <div className="text-4xl">🤝</div>
              <h1 className="mt-4 text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">Welcome to Envoy</h1>
              <p className="mt-3 text-base leading-relaxed text-[var(--color-ink-muted)]">
                Your agent searches, negotiates, and books the meetup for second-hand buys. Let's set up notifications so it can reach you.
              </p>
            </>
          )}

          {step === 1 && (
            <>
              <h1 className="text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">Connect Telegram</h1>
              <p className="mt-3 text-base leading-relaxed text-[var(--color-ink-muted)]">
                Get live pings when the seller replies or a meetup is proposed — and approve right from chat.
              </p>
              <div className="mt-7 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-4">
                {tgConnected ? (
                  <p className="text-sm font-medium text-[var(--color-primary)]">✓ Telegram connected — pings enabled.</p>
                ) : (
                  <p className="text-sm text-[var(--color-ink-muted)]">⏳ Waiting for you to tap <strong className="text-[var(--color-ink)]">Start</strong> in the bot…</p>
                )}
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div className="text-4xl">📅</div>
              <h1 className="mt-4 text-[2rem] font-bold leading-[1.1] tracking-[-0.02em] text-[var(--color-ink)]">Add to your calendar?</h1>
              <p className="mt-3 text-base leading-relaxed text-[var(--color-ink-muted)]">
                Optional. Connect Google Calendar so confirmed meetups appear automatically, with travel time accounted for.
              </p>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-3">
          {step === 0 && (
            <button type="button" onClick={() => setStep(1)} className={primaryBtn}>Get started</button>
          )}
          {step === 1 && (
            <>
              {!tgConnected && tgUrl && (
                <a href={tgUrl} target="_blank" rel="noreferrer" className={primaryBtn}>Open Telegram</a>
              )}
              {!tgConnected && tgUrl === '' && (
                <p className="text-center text-sm text-[var(--color-ink-muted)]">Telegram isn't configured — you can skip this for now.</p>
              )}
              <button type="button" onClick={() => setStep(2)} className={tgConnected ? primaryBtn : ghostBtn}>
                {tgConnected ? 'Continue' : 'Next'}
              </button>
            </>
          )}
          {step === 2 && (
            <>
              <button type="button" onClick={connectCalendar} className={primaryBtn}>Connect Calendar</button>
              <button type="button" onClick={finish} className={ghostBtn}>Maybe later</button>
            </>
          )}
        </div>
      </div>
    </main>
  )
}

const primaryBtn =
  'flex w-full cursor-pointer items-center justify-center rounded-xl bg-[var(--color-primary)] py-4 text-base font-semibold text-[var(--color-primary-text)] transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]'
const ghostBtn =
  'flex w-full cursor-pointer items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] py-3.5 text-base font-medium text-[var(--color-ink)] transition hover:bg-[var(--color-surface)] active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]'
```

- [ ] **Step 3: Verify build + type-check**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Build succeeds.

- [ ] **Step 4: Manual check**

Sign up a brand-new user. Expected: redirected to `/onboarding`; Welcome → Get started → Telegram step shows "Open Telegram" (or the "not configured" note if no bot env); Skip and "Maybe later" both land on `/search` and do not bounce back to onboarding (the gate sees `onboarded: true`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/screens/OnboardingWizard.tsx frontend/src/auth/AuthProvider.tsx
git commit -m "feat(frontend): onboarding wizard (welcome/telegram/calendar)"
```

---

## Task 11: Adapt InputScreen / HistoryScreen / SettingsScreen for tabs

**Files:**
- Modify: `frontend/src/screens/InputScreen.tsx`, `frontend/src/screens/HistoryScreen.tsx`, `frontend/src/screens/SettingsScreen.tsx`

- [ ] **Step 1: Remove the header nav icons from InputScreen**

In `frontend/src/screens/InputScreen.tsx`, delete the two `<button>` elements for History (lines ~178-189) and Settings (lines ~190-200), since those destinations now live in the bottom tab bar. Keep the `LanguageSwitcher` and "Agents ready" indicator. If `navigate` becomes unused after this, remove the `const navigate = useNavigate()` line and its import (line ~27 and the import) — only if no other usage remains (geolocation code does not use `navigate`).

> Verify no remaining references to `navigate(` in the file before removing the import.

- [ ] **Step 2: Remove the standalone Back button from HistoryScreen**

In `frontend/src/screens/HistoryScreen.tsx`, remove the `<BackButton label="Home" onClick={() => navigate('/')} />` (line ~108) and its `BackButton` import if now unused. The Deals tab no longer needs a back button (the tab bar handles navigation). Add a page title "Your deals" if one isn't already present at the top of the list.

- [ ] **Step 3: Remove the Back button + add Telegram row in SettingsScreen (Me tab)**

In `frontend/src/screens/SettingsScreen.tsx`:
- Remove the header `<button>` that calls `navigate('/')` with the back arrow (lines ~106-117) — the Me tab uses the tab bar.
- Add a Telegram status/connect row alongside the Google Calendar block. First add the imports and state:

```tsx
import { telegramStatus, telegramLinkToken } from '../api'
```

Add state near the other `useState` hooks:

```tsx
  const [tgConnected, setTgConnected] = useState<boolean | null>(null)
```

Add an effect near the `calendarStatus` effect:

```tsx
  useEffect(() => {
    if (!user) return
    telegramStatus().then((s) => setTgConnected(s.connected)).catch(() => setTgConnected(false))
  }, [user])
```

Add a connect handler near `connectCalendar`:

```tsx
  const connectTelegram = async () => {
    const { url } = await telegramLinkToken()
    if (url) window.open(url, '_blank', 'noopener')
  }
```

Add the row in the JSX right above the Google Calendar block:

```tsx
            {/* Telegram */}
            <div className="mt-7">
              <p className="mb-2 block text-sm font-medium text-[var(--color-ink)]">Telegram</p>
              {tgConnected ? (
                <p className="text-sm text-[var(--color-primary)]">Connected — you'll get negotiation pings in Telegram.</p>
              ) : (
                <button
                  type="button"
                  onClick={connectTelegram}
                  className="cursor-pointer rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-medium text-[var(--color-ink)] hover:bg-[var(--color-surface)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
                >
                  Connect Telegram
                </button>
              )}
            </div>
```

> The calendar OAuth still returns to `/settings?calendar=...`, which now redirects to `/me`. That's acceptable — the Me tab re-reads `calendarStatus()` on mount. No backend redirect change required.

- [ ] **Step 4: Verify build + type-check**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Build succeeds (no unused-variable errors).

- [ ] **Step 5: Manual check**

On `/search` confirm the header no longer shows the history/settings icons. On `/me` confirm the back button is gone and a "Connect Telegram" row appears (showing "Connected" once bound). On `/deals` confirm no back button.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/InputScreen.tsx frontend/src/screens/HistoryScreen.tsx frontend/src/screens/SettingsScreen.tsx
git commit -m "feat(frontend): adapt screens to tab shell; add Telegram row to Me"
```

---

## Task 12: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Backend suite green**

Run: `cd backend && python -m pytest -q`
Expected: All tests pass.

- [ ] **Step 2: Frontend build green**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Full manual demo pass**

With backend + frontend running and (ideally) `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME` set:
1. Sign up a new user → lands in onboarding wizard.
2. Telegram step → tap link → `/start <token>` in the bot → wizard flips to "✓ connected" within ~3s.
3. Continue → calendar step → "Maybe later" → lands on `/search` with bottom nav.
4. Run a deal to a seller reply → confirm the buyer ping arrives in the bound chat (not a stale global chat).
5. Tabs: Search ↔ Deal ↔ Me all work; nav stays visible during the negotiation checkpoint.
6. Reload app → onboarded user goes straight to `/search` (no wizard).

Expected: All steps behave as described.

- [ ] **Step 4: Commit any final fixups**

```bash
git add -A
git commit -m "chore: onboarding + mobile shell end-to-end verification fixups"
```

---

## Notes / Out of Scope (YAGNI)

- Email notifications (Gmail = login only).
- Push notifications / PWA install.
- Seller-side onboarding (seller stays role-based for the demo).
- Full translations for new copy — strings are inline English for now, matching the current mixed state; wire through `i18n/strings.ts` later if needed.
