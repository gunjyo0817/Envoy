# Envoy

**Your autonomous buying agent.** One command. Six AI agents. Three decisions. A confirmed deal in under 90 seconds.

Envoy compresses the entire second-hand buying process — search, ranking, negotiation, meetup coordination — into a single user input. You describe what you want. Envoy handles everything else and surfaces only the moments that require a human call.

---

## How it works

```
User input → Search → Extract → Analyst → [Checkpoint 1: Confirm candidate]
          → Negotiate → [Checkpoint 2: Confirm offer]
          → Coordinate → [Checkpoint 3: Confirm meetup]
          → Done
```

Six agents run autonomously via a LangGraph state machine. The buyer intervenes at exactly three structured checkpoints. All agent activity streams live to the UI over WebSocket.

---

## Tech stack

**Backend** — Python · FastAPI · LangGraph · SQLite · Google OAuth  
**Frontend** — React · TypeScript · Vite · Tailwind CSS  
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

Requires: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session` | Start a new buying session |
| `GET` | `/session/{id}/state` | Get current session state |
| `POST` | `/session/{id}/feedback` | Submit a checkpoint decision |
| `GET` | `/session/{id}/result` | Get the final result |
| `WS` | `/session/{id}/stream` | Stream real-time agent events |
| `POST` | `/auth/signup` | Create account |
| `POST` | `/auth/login` | Login |
| `GET` | `/auth/me` | Current user |
| `GET` | `/auth/google/login` | Google OAuth flow |
| `GET` | `/geocode/reverse` | Lat/lng → city name |
| `POST` | `/translate` | Translate text (Gemini) |
| `POST` | `/vision/identify` | Identify product from image (Gemini Vision) |

---

## Design

Dark mission control. Green for autonomous agent activity. Amber for human checkpoint moments. The color vocabulary teaches the interaction model without explanation.

See [DESIGN.md](DESIGN.md) for the full design system and [PRODUCT.md](PRODUCT.md) for product principles.

---

Built at Tech Europe Munich Hackathon 2026.
