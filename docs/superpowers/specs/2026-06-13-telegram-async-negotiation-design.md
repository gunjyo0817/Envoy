# Envoy — Async Telegram Negotiation + Onboarding, Calendar, History, Desktop

**Date:** 2026-06-13
**Status:** Approved design, pending implementation plan

## Summary

Envoy today runs the entire procurement flow **synchronously in one `graph.invoke()`** with a
**deterministic mock seller** ([backend/app/mock/seller.py](../../../backend/app/mock/seller.py)),
all state held **in memory** (`MemorySaver` + an in-memory `_sessions` dict). This design turns it
into a **two-sided, asynchronous** system: a real human seller responds over Telegram (assisted by an
AI agent), the buyer drives a polished web app and is bridged across async gaps by Telegram alerts,
and state is persisted so completed deals form a browsable history. It also adds Google Calendar–aware
meetup scheduling, an interactive two-sided reschedule flow, and a desktop landscape layout.

## Locked decisions

| Decision | Choice |
|----------|--------|
| Scope | All 7 features, sequenced by risk; cut from the bottom if time runs out |
| Seller UX on Telegram | Agent **suggests** a reply; seller **taps or edits** (`[Send €X] [Counter…] [Reject]`) |
| Buyer surface | **Web app primary**; Telegram = alerts only, with deep links back |
| Listing source | **Seed the seller's real item** (real photo/price/München), labeled Kleinanzeigen; image search matches the seed |
| Reschedule | Buyer proposes calendar-free slots → **seller picks one** on Telegram |
| Async engine | **Extend LangGraph `interrupt()`** to a seller turn; resume via Telegram handler |
| Telegram transport | **Long-polling** background worker; one bot, roles by `chat_id` |

## Architecture

### Persistence (replaces in-memory state)

- **Graph state:** `MemorySaver` → **`SqliteSaver`** (LangGraph native, same `thread_id` keying).
  State survives async gaps and server restarts.
- **New tables** in `envoy.db`:
  - `deals` — one row per closed session: `session_id`, `user_id`, `query`, `thumbnail`,
    `final_price`, `seller_label`, `meetup` (json), `status`, `created_at`, `closed_at`.
  - `telegram_links` — `chat_id`, `role` (`buyer`|`seller`), `user_id?`, `session_id?`.
  - `google_tokens` — `user_id`, `access_token`, `refresh_token`, `expiry`, `scope`.
- In-memory `_sessions` dict is retained as a hot cache; the DB is the source of truth.

### Async negotiation graph

The seller's turn — previously an instant mock call — becomes a **new `interrupt()`**:

```
make_offer → [BUYER interrupt: approve/lower/skip]
           → commit buyer offer → notify seller (Telegram)
           → [SELLER interrupt: send/counter/reject]    ← NEW, resumed by Telegram
           → decide_offer → (accept → meetup | counter → round 2 | reject → next candidate)
```

- Buyer checkpoints resume via existing `POST /session/{id}/feedback`.
- Seller turn resumes via the Telegram handler → `Command(resume=seller_choice)` on the same graph.
- New `status` value **`awaiting_seller`** (distinct from `awaiting_human`) so the buyer web UI shows a
  calm "Waiting for seller…" state over the existing WebSocket, not a checkpoint.
- Mock seller kept behind a `LIVE_SELLER` flag; when off, it auto-responds as today (keeps tests and
  offline dev green) and records this in `degraded`.

### Telegram layer

- **One bot**, long-polling background worker started with FastAPI (`asyncio` task; `python-telegram-bot`
  or raw `getUpdates`). Option to flip to webhooks on Railway later.
- **Registration:** seller `/start <session-or-listing-code>` → `telegram_links` row; buyer links Telegram
  in onboarding/settings via `/start <user-code>`.
- **Outbound:** `notify_seller(offer)` posts the AI-drafted reply + inline buttons;
  `notify_buyer(event)` posts "Seller replied — review ▸" with a web deep link.
- **Inbound handler:** button tap / text → resolve `chat_id` → role → session → resume graph (seller)
  or acknowledge (buyer alerts are read-only).

## Features

1. **Image search → seeded match.** `POST /vision/search` extends `identify_product`: photo → Gemini
   vision descriptor → matched against the seeded listing pool (seller's real item, labeled
   Kleinanzeigen) → feeds the normal `search → extract → analyst` flow unchanged. Seed lives in
   [backend/app/mock/listings.py](../../../backend/app/mock/listings.py).
2. **Telegram channel.** Buyer alerts + seller decision UI; one bot, long-polling (see Telegram layer).
3. **Async real-seller negotiation.** Seller-turn interrupt + `awaiting_seller` (see async graph).
4. **Google Calendar onboarding.** Add `calendar.readonly` to the existing Google OAuth scope; store in
   `google_tokens`. Post-login onboarding screen: "Connect your calendar so we never propose a busy
   time" (skippable → no-calendar degrade). `GET /calendar/freebusy?from&to` → Google FreeBusy → busy
   intervals.
5. **Interactive reschedule (two-sided).** "Suggest different time" opens a 7-day grid
   (morning/afternoon/evening); FreeBusy greys out busy slots; buyer taps 2–3 free slots →
   `POST /session/{id}/propose-times` → graph re-enters meetup planning → seller gets slots as Telegram
   buttons → taps one → confirmed both sides. Reuses the async interrupt pattern.
6. **History / past deals.** `GET /deals` (auth'd) from the `deals` table; a row is written on
   `done`/`failed`. New `HistoryScreen` (route `/history`): list with status chip, final price,
   thumbnail, meetup summary; tap → read-only detail (frozen thread + meetup).
7. **Desktop landscape layout.** Add a two-pane layout at `lg:` — left rail = agent activity/`StepBar`
   timeline, right = active screen. Reuses existing components; mobile unchanged.

## Demo script

1. Buyer uploads a photo → matches the seeded Kleinanzeigen listing. (①)
2. Agents run; buyer hits Checkpoint 1 (confirm candidate). (existing)
3. Agent drafts opening offer; buyer hits Checkpoint 2, taps *Send €X*; UI shows "Waiting for seller…". (③)
4. Seller's Telegram: offer + AI-drafted reply + buttons; seller taps *Counter*. (②)
5. Buyer's Telegram alert "Seller countered — review ▸"; buyer returns to web app, accepts.
6. Meetup: buyer taps *Suggest different time* → calendar-aware week grid → picks 2 slots. (④⑤)
7. Seller picks a slot on Telegram → confirmed both sides → Done + `deals` row written.
8. Open History → the closed deal alongside past ones, on the desktop two-pane layout. (⑥⑦)

## Risk-ordered build sequence

1. Persistence swap (SqliteSaver + 3 tables) — unblocks everything.
2. Seller-turn interrupt + `awaiting_seller` — async engine, mock fallback kept green.
3. Telegram layer (bot, long-polling, register, notify, resume handler) — demo spine.
4. Image search → seeded match — opening beat.
5. Buyer Telegram alerts + deep links — closes the async loop.
6. History view — judge-facing payoff, cheap once persistence exists.
7. Google Calendar onboarding + freebusy — enhancement.
8. Interactive week-picker reschedule — enhancement.
9. Desktop landscape layout — polish.

**Items 1–5 = demo works end-to-end. 6–9 = progressively nicer.** Each line is independently shippable.

## Out of scope / explicit non-goals

- Live scraping of Kleinanzeigen/Vinted (seeded listing instead).
- Real-time seller (the seller is genuinely async via Telegram).
- Webhook-based Telegram transport (long-polling for the hackathon; webhook is a later option).
- Seller-side web app or seller calendar integration.
