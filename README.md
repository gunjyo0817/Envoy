# Envoy

**Your autonomous buying agent.** Describe what you want. A coordinated team of AI agents searches listings, ranks candidates, negotiates price, and schedules a meetup — surfacing only the three decisions a human actually needs to make.

> Built at **Tech Europe Munich Hackathon 2026.**

---

## The Problem

Buying second-hand goods is still entirely manual. A typical purchase spans three or more platforms (Kleinanzeigen, Vinted, Facebook Marketplace), five or more repetitive steps per platform (search, compare, message, negotiate, schedule), and days of back-and-forth — all coordinated by the buyer, by hand, every single time.

The manual process has no leverage. Every deal costs roughly the same effort regardless of the item's value.

---

## The Solution

Envoy reduces that entire workflow to **one input and three decisions.**

```
"iPhone 14, max €400, Munich"
         ↓
  Search → Extract → Rank
         ↓
  [Decision 1: Confirm candidate]
         ↓
  Negotiate (fully autonomous)
         ↓
  [Decision 2: Accept offer]
         ↓
  Coordinate meetup
         ↓
  [Decision 3: Confirm meetup]
         ↓
  Done — Calendar invite added, receipt saved
```

A buyer types one sentence. Envoy finds the best deal across platforms, makes an opening offer, counters the seller autonomously until a price is agreed, then proposes a meetup time that fits both parties. The buyer approves three choices; everything else is handled.

Total time from input to confirmed deal: **under 90 seconds of buyer attention.**

---

## Business Context

| | Manual | Envoy |
|---|---|---|
| Platforms checked | 1–2 (by hand) | 3+ (parallel) |
| Buyer time per deal | 30–120 min | < 5 min |
| Negotiation | Skipped or manual | Autonomous, strategic |
| Deal tracking | None | Full history with receipts |
| Meetup coordination | Manual DMs | Agent-proposed, calendar-synced |

**Market fit:** The European second-hand market is €80B+/year and growing. The bottleneck is not supply or demand — it's friction. Envoy removes the friction entirely for the buyer side.

**Moat:** The value compounds over time. Each deal trains preferences (budget anchors, preferred conditions, trusted seller signals). A returning user gets a buying agent that already knows them.

**Expansion paths:** Seller-side agent (auto-list + negotiate inbound offers), fleet procurement for small businesses, subscription for power buyers.

---

## How It Works

### Agent Pipeline

Five specialist agents run sequentially as a **LangGraph state machine**, each handing off structured state to the next:

| Agent | What it does | AI used |
|-------|-------------|---------|
| `search` | Queries Tavily for live listings across platforms; two queries run in parallel | — |
| `extract` | Parses raw listing HTML/JSON into structured product records (price, condition, seller rating, location); up to 8 listings extracted concurrently | Gemini Vision |
| `analyst` | Scores candidates on a weighted rubric (price fit 40%, condition 30%, seller trust 20%, distance 10%); generates a buyer-facing insight per candidate | Gemini |
| `negotiate` | Opens at 80–90% of listing price; counters autonomously; adapts strategy based on seller responses; writes messages in the seller's language | Claude + Gemini |
| `coordinate` | Proposes meetup times from the buyer's calendar free/busy; suggests a midpoint location | Claude |

Human checkpoints sit between agents at the three decision points (candidate → offer → meetup). The buyer can approve from the **web UI or directly via Telegram reply**.

### Scoring Formula

```
score = price_fit × 0.40
      + condition  × 0.30
      + seller_trust × 0.20
      + proximity   × 0.10
```

`price_fit` scales linearly from budget min to max. `condition` maps `new → 1.0` down to `acceptable → 0.5`. `seller_trust` combines seller rating (70%) and review count capped at 50 (30%). `proximity` decays linearly to zero at 20 km.

### Negotiation Logic

The negotiate agent starts below listing price, tracks the counter-offer thread, and computes a counter that closes the gap geometrically toward the buyer's max budget. It classifies each seller message (accept / counter / reject / ignore) using a small Gemini call and writes reply text in the seller's detected language. If the seller rejects twice or goes above budget, it escalates to the buyer.

### Real-Time Updates

Every state transition and agent log event is pushed to the frontend over a **WebSocket** (`/session/{id}/stream`). The UI streams agent activity live — the buyer watches Envoy work rather than staring at a spinner.

---

## Tech Stack

### Backend

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | FastAPI 0.137 + Starlette 1.0.1 | Async-native, WebSocket support, fast |
| Agent orchestration | LangGraph | Stateful graph with interrupt/resume for human checkpoints |
| Database | SQLite (stdlib) | Zero-dependency, sufficient for hackathon scale |
| Auth | Custom JWT-style tokens + Google OAuth | Email/password and social login |
| AI — negotiation & analysis | Claude (claude-opus-4) | Best-in-class reasoning and tone |
| AI — extraction & translation | Gemini (gemini-3.5-flash) | Fast, cheap, vision-capable |
| Search | Tavily API | Real-time web search with structured results |
| Notifications | Telegram Bot API | Async push without requiring mobile app |
| Calendar | Google Calendar API | Free/busy queries + event creation |

### Frontend

| Layer | Choice |
|-------|--------|
| Framework | React 19 + TypeScript |
| Build | Vite |
| Styling | Tailwind CSS 4 |
| Routing | React Router 7 (SPA, three-tab shell) |
| State | React Context (auth) + custom `useSession` hook (WebSocket + polling) |

### Infrastructure

| Service | Role |
|---------|------|
| Railway | Backend (Python) — auto-deploy from `main` |
| Vercel | Frontend (static SPA) — auto-deploy from `main` |
| Nix (nixpacks) | Build env on Railway — `stdenv.cc.cc.lib` for grpcio/libstdc++ |

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Frontend (Vercel)                       │
│  React SPA — 3-tab shell                │
│  Search / Deal / Me                     │
│                                          │
│  ┌──────────┐  WebSocket  ┌──────────┐  │
│  │ UI state │ ←─────────→ │ FastAPI  │  │
│  └──────────┘             └──────────┘  │
└───────────────────────────┬─────────────┘
                            │ HTTP / WS
┌───────────────────────────▼─────────────┐
│  Backend (Railway)                       │
│                                          │
│  FastAPI  ──►  LangGraph state machine   │
│                                          │
│  ┌────────┐ ┌─────────┐ ┌──────────┐   │
│  │ search │ │ extract │ │ analyst  │   │
│  └────┬───┘ └────┬────┘ └────┬─────┘   │
│       └──────────┴───────────┘          │
│  ┌───────────┐    ┌────────────┐        │
│  │ negotiate │───►│ coordinate │        │
│  └───────────┘    └────────────┘        │
│                                          │
│  SQLite ── Auth ── Telegram ── GCal     │
└─────────────────────────────────────────┘
```

### Key Design Decisions

**SQLite over Postgres** — a single process, no connection pool overhead, zero provisioning. For the demo scale this is strictly faster and simpler.

**LangGraph interrupts for checkpoints** — rather than polling or callbacks, the agent graph suspends execution at `interrupt()` calls and resumes when the buyer submits feedback. State is fully serializable; sessions survive server restarts.

**Parallel extraction with ThreadPoolExecutor** — Gemini calls for individual listings are independent. Running 8 concurrently collapses 8× serial latency to ~1 round-trip. Processing time dropped from ~40s to ~10s.

**Per-user Telegram binding via deep link** — each user gets a unique `t.me/<bot>?start=<token>` URL. When they tap it, the bot maps their Telegram chat ID to their user account. No shared group chats; notifications are private and per-user.

**OnboardingGate strict equality** — the gate fires only when `user.onboarded === false`. `undefined` (users from before the `onboarded` field was added) is treated as already onboarded, preventing false redirects for existing sessions.

---

## Features

### Core
- **Autonomous 5-agent pipeline** — search → extract → rank → negotiate → coordinate
- **Three human checkpoints** — approve candidate, accept offer, confirm meetup
- **Live agent log** — WebSocket-streamed activity feed in the UI
- **Multi-platform search** — Kleinanzeigen, Vinted, Facebook Marketplace (via Tavily)
- **Listing links** — real Kleinanzeigen URLs with one-tap "View listing" links in the UI

### Notifications
- **Telegram** — per-user binding via personal deep link; approve checkpoints directly from chat
- **Google Calendar** — confirmed meetups added automatically with travel time

### Account & UX
- **Email/password + Google sign-in**
- **Onboarding wizard** — skippable 3-step flow on first login (welcome → Telegram → Calendar); incomplete steps accessible from the Me tab
- **Mobile-first 3-tab shell** — Search / Deal / Me with persistent bottom navigation
- **Deal history** — full session timeline with receipt and agent transcript
- **Admin panel** — session monitoring and manual overrides

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- API keys: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` (Gemini), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `TAVILY_API_KEY`

### Backend

```bash
cd backend
pip install -e .
cp .env.example .env   # fill in API keys
uvicorn app.main:app --reload
```

The backend starts at `http://localhost:8000`. SQLite database is created automatically on first run.

**Optional — Telegram notifications:**

```env
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_BOT_USERNAME=<your-bot-username>   # without @
```

Without these, the app runs fully; the onboarding Telegram step is skippable.

**Optional — live seller (for demos):**

```env
LIVE_SELLER=true   # real Telegram seller; omit to use mock auto-replies
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. Set `VITE_API_URL` in `frontend/.env` to point at a non-local backend.

### Tests

```bash
cd backend && pytest   # 86 tests
```

---

## API Reference

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session` | Start a new buying session |
| `GET` | `/session/{id}/state` | Get current session state |
| `POST` | `/session/{id}/feedback` | Submit a checkpoint decision (approve / reject / free text) |
| `POST` | `/session/{id}/propose-times` | Submit buyer's available meetup slots |
| `GET` | `/session/{id}/result` | Final deal result |
| `WS` | `/session/{id}/stream` | Stream real-time agent events |

### Auth & Account

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/signup` | Create account (email + password) |
| `POST` | `/auth/login` | Log in; returns session token |
| `GET` | `/auth/me` | Current user (includes `onboarded` flag) |
| `GET` | `/auth/google/login` | Start Google OAuth flow |
| `GET` | `/auth/google/callback` | OAuth callback |
| `GET` / `PUT` | `/settings` | Read / update user preferences |
| `POST` | `/onboarding/complete` | Mark onboarding as finished |

### Notifications & Calendar

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/telegram/link-token` | Mint a personal deep-link token for Telegram binding |
| `GET` | `/telegram/status` | Whether the current user's Telegram chat is bound |
| `GET` | `/calendar/auth-url` | Start Google Calendar OAuth |
| `GET` | `/calendar/status` | Whether Calendar is connected |
| `POST` | `/calendar/event` | Add a confirmed meetup to the calendar |
| `GET` | `/calendar/freebusy` | Query buyer's busy times for a date range |

### Deals & Utilities

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/deals` | List the current user's completed deals |
| `GET` | `/deals/{id}` | Get a single deal with full session transcript |
| `GET` | `/geocode/reverse` | Lat/lng → city name |
| `POST` | `/translate` | Translate text via Gemini |
| `POST` | `/vision/identify` | Identify product from image (Gemini Vision) |
| `POST` | `/vision/search` | Identify product from image and start a search |

---

## Environment Variables

### Backend

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ | Claude (negotiation, coordination) |
| `GOOGLE_API_KEY` | ✅ | Gemini (extraction, translation, vision) |
| `TAVILY_API_KEY` | ✅ | Real-time listing search |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth (sign-in + Calendar) |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth |
| `FRONTEND_URL` | ✅ | OAuth redirect target (e.g. `https://your-app.vercel.app`) |
| `TELEGRAM_BOT_TOKEN` | optional | Enable Telegram notifications |
| `TELEGRAM_BOT_USERNAME` | optional | Bot username (without @) for deep links |
| `LIVE_SELLER` | optional | `true` = real Telegram seller; default = mock |
| `ENVOY_MAX_EXTRACT` | optional | Max listings to extract concurrently (default 8) |

### Frontend

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend base URL (default: `http://localhost:8000`) |

---

## Deployment

### Railway (Backend)

1. Create a Railway project and point it at this repo.
2. Set all required environment variables in Railway's dashboard.
3. Railway auto-deploys on push to `main` using `nixpacks.toml` (which adds `stdenv.cc.cc.lib` for grpcio) and `railway.json` (which uses `/opt/venv/bin/uvicorn`).

Add `GOOGLE_REDIRECT_URI=https://<your-railway-domain>/auth/google/callback` and `CALENDAR_REDIRECT_URI=https://<your-railway-domain>/calendar/callback` to the Google Cloud Console's authorised redirect URIs.

### Vercel (Frontend)

1. Import the repo into Vercel; set **Root Directory** to `frontend`.
2. Set `VITE_API_URL` to your Railway backend URL.
3. `frontend/vercel.json` already includes the SPA catch-all rewrite — no extra config needed.

---
