# Envoy

**Your autonomous buying agent.** One command. A team of AI agents. Three decisions. A confirmed deal in under 90 seconds.

Envoy compresses the entire second-hand buying process — search, ranking, negotiation, meetup coordination — into a single user input. You describe what you want. Envoy handles everything else and surfaces only the moments that require a human call, pinging you on Telegram when the seller responds.

---

## How it works

```
User input → Search → Extract → Analyst → [Checkpoint 1: Confirm candidate]
          → Negotiate → [Checkpoint 2: Confirm offer]
          → Coordinate → [Checkpoint 3: Confirm meetup]
          → Done
```

Agents run autonomously via a LangGraph state machine. The buyer intervenes at exactly three structured checkpoints. All agent activity streams live to the UI over WebSocket, and the buyer can approve checkpoints from the web app or directly from Telegram.

---

## Features

- **Autonomous agent pipeline** — search → extract → rank → negotiate → coordinate, with three human checkpoints.
- **Mobile-app shell** — a persistent three-tab interface: **Search** (start/resume a deal), **Deal** (in-progress + completed deals), **Me** (profile & settings).
- **New-user onboarding** — a skippable wizard that connects notification channels on first sign-up; unfinished steps stay reachable from the Me tab.
- **Telegram notifications** — per-user binding via a personal deep link. Buyers get live pings when the seller replies or a meetup is proposed, and can approve right from chat.
- **Google Calendar** — optional connect so confirmed meetups land on the buyer's calendar, with travel time accounted for.
- **Auth** — email/password or Google sign-in.
- **Live updates** — real-time agent logs and state over WebSocket.

---

## Tech stack

**Backend** — Python · FastAPI · LangGraph · SQLite · Google OAuth · Telegram Bot API
**Frontend** — React · TypeScript · Vite · Tailwind CSS · React Router
**AI** — Claude (negotiation, analysis) · Gemini (translation, vision/product identification)
**Real-time** — WebSocket session streaming

---

## Agents

| Agent | Role |
|-------|------|
| `search` | Finds candidate listings matching the user's query and location |
| `extract` | Parses raw listings into structured product data |
| `analyst` | Ranks candidates and selects the best match |
| `negotiate` | Makes and counters offers autonomously; stops at deal or rejection |
| `coordinate` | Proposes meetup time and location with the seller |

---

## Getting started

### Backend

```bash
cd backend
pip install -e .
cp .env.example .env   # fill in API keys
uvicorn app.main:app --reload
```

**Required:** `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

**Optional (notifications):** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` — enable Telegram pings and per-user binding deep links. Without them the app still runs; the onboarding Telegram step is skippable.

Run the test suite with `pytest` from the `backend/` directory.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## API

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session` | Start a new buying session |
| `GET` | `/session/{id}/state` | Get current session state |
| `POST` | `/session/{id}/feedback` | Submit a checkpoint decision |
| `POST` | `/session/{id}/propose-times` | Propose meetup time slots |
| `GET` | `/session/{id}/result` | Get the final result |
| `WS` | `/session/{id}/stream` | Stream real-time agent events |

### Auth & account

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/signup` | Create account |
| `POST` | `/auth/login` | Login |
| `GET` | `/auth/me` | Current user |
| `GET` | `/auth/google/login` | Google OAuth flow |
| `GET` / `PUT` | `/settings` | Read / update user settings |
| `POST` | `/onboarding/complete` | Mark onboarding finished |

### Notifications & calendar

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/telegram/link-token` | Mint a personal Telegram deep-link token |
| `GET` | `/telegram/status` | Whether the user's Telegram chat is bound |
| `GET` | `/calendar/auth-url` | Start Google Calendar connect |
| `GET` | `/calendar/status` | Whether Calendar is connected |
| `POST` | `/calendar/event` | Add a meetup to the calendar |
| `GET` | `/calendar/freebusy` | Query busy times |

### Deals & utilities

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/deals` | List the user's deals |
| `GET` | `/deals/{id}` | Get a single deal |
| `GET` | `/geocode/reverse` | Lat/lng → city name |
| `POST` | `/translate` | Translate text (Gemini) |
| `POST` | `/vision/identify` | Identify product from image (Gemini Vision) |
| `POST` | `/vision/search` | Identify and match a listing from an image |

---

Built at Tech Europe Munich Hackathon 2026.
