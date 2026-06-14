# Onboarding + Mobile App Shell — Design

**Date:** 2026-06-14
**Project:** Envoy (BuyBot) — AI procurement agent
**Scope:** New-user onboarding wizard + mobile-app-style 3-tab bottom navigation.

## Goal

Make Envoy feel like a phone app and ensure new users connect the channels the
agent needs to reach them. Two pieces:

1. A **skippable onboarding wizard** shown once after first signup, to connect
   Telegram (notifications) and optionally Google Calendar.
2. A persistent **bottom tab bar** with three tabs — Search, Deal, Me — wrapping
   the existing screens in a native-feeling shell.

## Decisions (locked during brainstorming)

- **App shell:** Approach A — persistent tab shell with nested routes (a layout
  route renders `<BottomNav>` + `<Outlet>`).
- **Bottom nav visibility:** Always visible, including during an active
  negotiation/checkpoint (truest app feel).
- **Notification channels:** Telegram is the only real notification channel.
  "Gmail binding" = the Google account, which is already established at login;
  no separate email-notification system.
- **Telegram binding:** Real **per-user** binding via a deep-link token
  (`t.me/<bot>?start=<token>`), not the current global role-based binding.
- **Onboarding:** Skippable wizard. Every step can be skipped and finished later
  from the Me tab.
- **Google Calendar:** Optional step; this OAuth also serves as the Google link
  for email-signup users.

## Architecture

### Routing (`frontend/src/App.tsx`)

Introduce a layout route that owns the bottom nav:

```
/onboarding          → OnboardingWizard (full screen, no tab bar)
/                    → AppShell (renders <BottomNav/> + <Outlet/>)
  index → redirect to /search
  /search            → SearchTab (current BuyerFlow: input → … → done)
  /deals             → DealsTab (current HistoryScreen, renamed)
  /deals/:sessionId  → DealDetail
  /me                → MeTab (current SettingsScreen)
/admin               → AgentView (unchanged)
```

- Legacy paths `/history` and `/settings` redirect to `/deals` and `/me`.
- Auth gate stays: unauthenticated users see `AuthScreen` regardless of route.
- **Onboarding gate:** after auth, if the user `needs_onboarding` (see below) and
  is not already on `/onboarding`, redirect to `/onboarding`.

### Tabs

| Tab | Icon | Content | Source today |
|-----|------|---------|--------------|
| Search | 🔍 | Buyer flow entry (query/budget/location/photo). In-progress deal resumes here. | `BuyerFlow` / `InputScreen` |
| Deal | 🤝 | All deals — in-progress (status pills) + done. Tap → detail. | `HistoryScreen` (extended to show live deals) |
| Me | 👤 | Profile + settings: Telegram status, Calendar status, language, default address, logout. Onboarding nudge badges. | `SettingsScreen` |

The buyer flow's internal state machine (searching → reviewing → awaiting_human →
… → done) is unchanged; it simply lives inside the Search tab while the bottom
nav remains mounted around it.

### Onboarding wizard (`OnboardingWizard`)

A full-screen, 3-step flow with a step indicator and a per-step "Skip":

1. **Welcome** — one line on what Envoy does; "Get started."
2. **Connect Telegram** — shows the user's personal deep link
   `t.me/<bot>?start=<token>` and an "Open Telegram" button. Polls binding
   status; the card flips to a ✓ "connected" state automatically when the user
   taps Start in the bot. Skippable.
3. **Add to calendar? (optional)** — "Connect Google Calendar" (reuses the
   existing calendar OAuth) or "Maybe later."

On finish or skip-through, set the user's `onboarded` flag and route to `/search`.

## Backend changes

### Per-user Telegram binding

Current state: `telegram_links(chat_id, role, user_id, session_id)` exists with a
`user_id` column, but `/start <role>` registration never sets `user_id`, and
`notify_buyer` routes via `chat_for_role("buyer")` (global, last-registered).

Changes:

1. **Binding token.** Add an endpoint `POST /telegram/link-token` (auth required)
   that mints a short-lived random token mapped to the caller's `user_id`
   (in-memory dict like `auth._TOKENS`, or a small table). Return the token and
   the full deep-link URL `t.me/<BOT_USERNAME>?start=<token>`.
   - Requires `TELEGRAM_BOT_USERNAME` in env (alongside `TELEGRAM_BOT_TOKEN`).
2. **`/start <token>` handler** (`telegram._dispatch`): if the argument resolves
   to a pending link token, call `store.register_chat(chat_id, "buyer", user_id)`
   and confirm in chat. Keep the existing `/start seller` path for the seller
   side (seller stays role-based — it's the demo counterparty).
3. **Per-user routing.** Add `store.chat_for_user(user_id)` and make
   `notify_buyer(session_id, message)` resolve the buyer chat by the session's
   `user_id` (sessions already carry `user_id`; if not, thread it through).
   Fall back to `chat_for_role("buyer")` if no per-user chat (keeps current demo
   working).
4. **Binding status.** `GET /telegram/status` (auth) → `{ connected: bool, handle? }`
   so the wizard and Me tab can poll/show state.

### Onboarding flag

Add `onboarded INTEGER NOT NULL DEFAULT 0` to `users` (migration in
`auth.init_db`, mirroring the existing `ALTER TABLE` pattern in `store.init_store`).

- Expose on the auth user payload (`_public_user`) as `onboarded: bool`.
- `POST /onboarding/complete` (auth) sets it to 1 (called on finish/skip-through).
- `needs_onboarding` (frontend) = `user.onboarded === false`. (Telegram-connected
  state is shown inside the wizard but does not by itself gate the wizard.)

## Data flow

- **Wizard → Telegram:** wizard calls `/telegram/link-token` → renders deep link
  → user taps Start in Telegram → bot `/start <token>` binds chat to user_id →
  wizard polls `/telegram/status` → flips to ✓.
- **Wizard → Calendar:** "Connect Calendar" reuses existing `calendarAuthUrl()`
  redirect flow; on return, `calendarStatus()` reflects connected.
- **Notifications:** `notify_buyer` now routes to the session owner's bound chat.

## Frontend components

- `AppShell` — layout route: `<Outlet/>` + `<BottomNav/>`.
- `BottomNav` — three tab links with active state; uses `NavLink`.
- `OnboardingWizard` — step state, step indicator, skip handling.
- `OnboardingGate` — small wrapper/effect that redirects to `/onboarding` when
  `needs_onboarding`.
- Reuse/rename: `HistoryScreen` → Deals tab content; `SettingsScreen` → Me tab
  content (drop its standalone back button; it's a tab now). Add Telegram
  connect/status row to the Me tab.
- API additions in `api.ts`: `telegramLinkToken()`, `telegramStatus()`,
  `completeOnboarding()`.

## Error handling

- **Telegram not configured** (`TELEGRAM_BOT_TOKEN`/`TELEGRAM_BOT_USERNAME`
  missing): wizard still renders, link-token endpoint returns a clear "not
  configured" state; the step shows a graceful message and remains skippable.
  `notify_buyer` already no-ops without a token.
- **Token expired / not tapped:** status stays "waiting"; user can regenerate the
  link or skip. Wizard never dead-ends.
- **Calendar OAuth failure:** existing `auth_error` handling; step remains
  skippable.
- **Already-onboarded user hitting `/onboarding`:** redirect to `/search`.

## Testing

- **Backend:** unit tests for `link-token` mint/resolve, `/start <token>` binding
  sets `user_id`, `chat_for_user` routing, `notify_buyer` fallback, and
  `onboarding/complete` flag flip.
- **Frontend:** onboarding gate redirects new users and not returning ones;
  bottom nav active states; legacy route redirects; wizard skip paths reach
  `/search`.
- **Manual demo pass:** signup → wizard → tap Telegram link → see ✓ → connect
  calendar → land on Search; run a deal and confirm the buyer ping arrives in the
  bound chat.

## Out of scope (YAGNI)

- Email notifications (Gmail = login only).
- Push notifications / PWA install.
- Seller-side onboarding (seller stays role-based for the demo).
- Multi-language copy for the new screens beyond the existing i18n pattern
  (wire strings through `i18n/strings.ts`, but full translations can follow).
