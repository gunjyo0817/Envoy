# AI Procurement Agent — Design Spec

**Date:** 2026-06-13  
**Hackathon:** Tech Europe Munich (24h)  
**Focus:** Multi-agent + human-in-the-loop + real buyer utility

---

## 1. Problem & Goal

Buying second-hand items in Europe involves hours of cross-platform searching, price research, back-and-forth negotiation, and meetup coordination. The goal is to compress this entire process into a single user input, with agents handling everything and surfacing decisions only when human judgment is required.

---

## 2. Approach

**A — Full pipeline with hybrid data.**  
All four agent roles implemented end-to-end. Kleinanzeigen is queried live via Tavily; Vinted is attempted with a pre-scraped fallback; Facebook Marketplace uses a prepared mock dataset. The demo shows a complete buyer journey from input to confirmed meetup.

This approach was chosen over live-only scraping (too brittle for demo) and LLM-simulated sellers (unpredictable pacing) because it maximises the number of human-in-the-loop checkpoints visible to judges within 24 hours.

---

## 3. Architecture

### 3.1 Agent Roles

| Agent | Responsibility | Tool |
|-------|---------------|------|
| **Orchestrator** | LangGraph state machine, routing, interrupt management | Gemini |
| **Search Agent** | Cross-platform listing discovery | Tavily |
| **Extract Agent** | Raw listings → structured schema | Pioneer / GLiNER2 |
| **Analyst Agent** | Scoring, ranking, insight generation | Gemini |
| **Negotiation Agent** | Offer strategy, message generation, classifying seller replies | Gemini + GLiNER2 |
| **Coordination Agent** | Meetup time/location proposal, route calculation | Gemini + Google Maps API |

**Partner tool story for judges:**
- **Tavily = eyes** — live market awareness, LLM-ready content with no HTML noise
- **Pioneer/GLiNER2 = muscle** — high-frequency structured extraction at ~100ms/listing, ~100× cheaper than Gemini for this task
- **Gemini = brain** — strategy, dialogue, summarising context into one human-readable sentence per checkpoint

### 3.2 Human Checkpoints

Three `interrupt()` nodes pause the graph and surface a structured decision:

| # | Checkpoint key | What the agent asks |
|---|----------------|---------------------|
| 1 | `confirm_candidate` | "Found iPhone 14 from €175 — start negotiating?" |
| 2 | `confirm_offer` | "Seller countered at €185 — accept, counter lower, or move on?" |
| 3 | `confirm_meetup` | "Seller near Marienplatz, Sat 2pm. You're 12min away by bike. Confirm?" |

### 3.3 Pioneer / GLiNER2 Eval Table

Run both models on the same extraction task (listing → schema, seller message → act classification) and record accuracy / latency / cost. This single table serves two purposes: Pioneer prize evidence and Atira technical complexity score.

---

## 4. LangGraph State

```python
class ProcurementState(TypedDict):
    # ── Input ────────────────────────────────────────────────
    query: str                   # "iPhone 14"
    budget: float                # 200.0
    condition: str               # "good+"
    location: str                # "München"
    max_distance_km: int         # 15

    # ── Search ───────────────────────────────────────────────
    raw_listings: list[dict]           # Tavily raw output
    structured_listings: list[dict]    # GLiNER2 parsed

    # ── Analysis ─────────────────────────────────────────────
    ranked_candidates: list[dict]      # scored, sorted list
    current_candidate_index: int       # pointer into ranked_candidates
                                       # incremented when a negotiation fails

    # ── Negotiation ──────────────────────────────────────────
    negotiation_thread: list[NegotiationMessage]
    final_price: float | None

    # ── Coordination ─────────────────────────────────────────
    meetup_proposal: dict | None       # {location, time, buyer_route, seller_route}
    confirmed: bool

    # ── Human-in-the-loop ────────────────────────────────────
    pending_decision: PendingDecision | None   # set by interrupt(), cleared on resume
    decision_history: list[dict]               # full audit trail, useful for demo replay
    human_feedback: str | None                 # free-text supplement (optional)

    # ── Control ──────────────────────────────────────────────
    status: Literal[
        "searching", "reviewing", "awaiting_human",
        "negotiating", "coordinating", "done", "failed"
    ]
    degraded: list[str]   # e.g. ["tavily_fallback_to_mock", "gliner2_fallback_to_gemini"]
```

### 4.1 PendingDecision schema

```python
class PendingDecision(TypedDict):
    checkpoint: str          # "confirm_candidate" | "confirm_offer" | "confirm_meetup"
    summary: str             # Gemini-generated one-liner shown to user
    options: list[dict]      # [{"id": "approve", "label": "同意出價"}, ...]
    context: dict            # raw data the frontend/handler can use if needed
```

When `interrupt()` fires, the Orchestrator sets `status = "awaiting_human"` and populates `pending_decision`. The frontend sees `awaiting_human`, reads `pending_decision`, renders the options, and waits. On user action, `POST /session/{id}/feedback` carries `{"choice": "approve"}`, the graph resumes, and the decision is appended to `decision_history`.

### 4.2 NegotiationMessage schema

```python
class NegotiationMessage(TypedDict):
    role: Literal["buyer", "seller"]
    text: str
    act: Literal[
        "initial_offer", "counter_offer", "accept",
        "reject", "question", "stall"
    ]                        # GLiNER2 classification result
    price: float | None      # extracted numeric price if present
    ts: str                  # ISO timestamp
```

`act` and `price` are the fields that feed the Negotiation Agent's strategy logic and populate the GLiNER2 eval table.

---

## 5. API Design

```
POST /session                       Create session, return session_id
GET  /session/{id}/state            Full LangGraph state (source of truth)
POST /session/{id}/feedback         Submit human checkpoint decision
                                    body: {"choice": str, "free_text": str | None}
WS   /session/{id}/stream           Lightweight activity events only —
                                    never full state. On disconnect, client
                                    falls back to polling GET /state.
GET  /session/{id}/result           Final confirmed meetup info
```

**WebSocket event shape (lightweight, not state):**

```json
{"event": "state_changed", "status": "awaiting_human"}
{"event": "agent_log", "agent": "extract", "msg": "Parsed 23 listings in 2.1s"}
```

Frontend rule: WS events trigger `GET /state` for truth. WS never carries full state to avoid divergence.

---

## 6. Data Sources

| Platform | Strategy |
|----------|----------|
| Kleinanzeigen | Live via Tavily on every search |
| Vinted | Tavily attempt; pre-scraped fallback if rate-limited |
| Facebook Marketplace | Pre-prepared 5-listing mock dataset (login-gated, not scrapeable reliably) |

---

## 7. Frontend

**Tech:** React + Vite + Tailwind CSS  
**Transport:** WebSocket (activity feed) + polling GET /state every 2s (reliability fallback)

### Screens in demo video order

1. **Input** — query, budget slider, condition, location
2. **Processing** — step progress bar, friendly status messages (no technical agent names)
3. **Choose** (Human CP 1) — top 3 result cards with Gemini insight, one-tap action
4. **Negotiating** — chat-style thread showing buyer/seller exchange, current offer highlighted
5. **Offer decision** (Human CP 2) — accept / counter lower / skip this seller
6. **Meetup** (Human CP 3) — map, time options, route summary, confirm button
7. **Done** — face-to-face details, share/save

**Agent view (for demo video):** A separate `/admin` route shows the full agent activity feed with tool badges (TAVILY, GEMINI, PIONEER). The 2-min video cuts to this briefly to show the multi-agent story, then returns to the buyer UI.

---

## 8. Fallback & Robustness

| Failure | Fallback |
|---------|----------|
| Tavily timeout / quota | Serve pre-scraped mock listing set; record `"tavily_fallback_to_mock"` in `degraded` |
| GLiNER2 extraction fails | Call Gemini for the same extraction; record `"gliner2_fallback_to_gemini"` |
| Gemini timeout | Retry once (5s); if still failing, surface error in status |
| Negotiation rejected | Increment `current_candidate_index`, restart negotiation with next ranked candidate |
| WS disconnect | Frontend falls back to 2s polling on GET /state; no data loss |

`degraded` is visible in the demo UI's agent view. During the pitch, this becomes a talking point about robustness rather than a hidden failure.

---

## 9. Security (Aikido)

Connect Aikido to the repo on Day 1. Key risks this project carries:

- API keys in environment (Tavily, Gemini, Google Maps) — Aikido will flag any committed secrets
- Tavily crawling external URLs — SSRF risk if user input flows directly into fetch calls
- FastAPI endpoints — no auth needed for hackathon, but input validation required

Run Aikido scan before submission, fix flagged issues, screenshot the clean report for the Aikido prize (€1000, ~zero product time cost).

---

## 10. Demo Video Script (2 min)

| Time | Screen | Narration focus |
|------|--------|-----------------|
| 0:00–0:20 | Input | User types "iPhone 14, €200, München" and hits go |
| 0:20–0:35 | Agent view | Cut to admin route — show 5 agents activating with tool badges; call out Tavily/GLiNER2/Gemini division of labour |
| 0:35–1:00 | Choose (CP1) | Results appear; "agents found 23 listings, best is 12% below market" |
| 1:00–1:25 | Negotiate (CP2) | Seller counters; user taps "counter lower"; agent replies |
| 1:25–1:45 | Meetup (CP3) | Proposed location on map, confirm |
| 1:45–2:00 | Done | "From search to confirmed meetup in under 90 seconds" |

---

## 11. Out of Scope (for 24h)

- Real-time seller messaging integration (simulated in demo)
- User accounts / persistent history
- Payment handling
- iOS/Android app
- More than 3 platforms
