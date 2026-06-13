# AI Procurement Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an end-to-end AI procurement agent that takes a product description + budget and autonomously searches, ranks, negotiates, and coordinates a meetup — surfacing three structured human-in-the-loop checkpoints along the way.

**Architecture:** LangGraph StateGraph orchestrates six agents (Search → Extract → Analyst → Negotiate → Coordinate) with `interrupt()` nodes at three checkpoints. Tavily handles live search, Pioneer/GLiNER2 handles high-frequency structured extraction, and Gemini handles strategy and dialogue. FastAPI + WebSocket serves the React frontend.

**Tech Stack:** Python 3.11, LangGraph 0.2, FastAPI, Uvicorn, Tavily Python SDK, `google-generativeai`, `gliner` package (GLiNER2), React 18, Vite, Tailwind CSS, `react-router-dom`.

---

## File Map

```
backend/
  pyproject.toml              # all Python deps
  .env.example
  app/
    main.py                   # FastAPI app, all routes + WebSocket
    state.py                  # ProcurementState, NegotiationMessage, PendingDecision
    graph.py                  # StateGraph definition, compile with MemorySaver
    sessions.py               # session_id → thread_id store, log_event() helper
    agents/
      search.py               # search_node: Tavily + fallback
      extract.py              # extract_node: GLiNER2 + Gemini fallback
      analyst.py              # analyst_node: Gemini scoring + ranking
      negotiate.py            # negotiate_node: Gemini strategy + GLiNER2 classification
      coordinate.py           # coordinate_node: Gemini + Google Maps
    mock/
      listings.py             # FB Marketplace mock + Vinted fallback data
      seller.py               # deterministic mock seller response function
  tests/
    test_state.py
    test_search.py
    test_extract.py
    test_analyst.py
    test_negotiate.py
    test_api.py

frontend/
  package.json
  vite.config.ts
  tailwind.config.ts
  src/
    main.tsx
    App.tsx                   # router: / and /admin
    api.ts                    # createSession, getState, postFeedback, connectWS
    useSession.ts             # React hook: polls state + manages WS
    screens/
      InputScreen.tsx
      ProcessingScreen.tsx
      ChooseScreen.tsx        # CP1
      NegotiateScreen.tsx     # negotiation thread + CP2 banner
      MeetupScreen.tsx        # CP3
      DoneScreen.tsx
    components/
      StepBar.tsx
      ListingCard.tsx
      CheckpointBanner.tsx    # renders pending_decision.options as action buttons
      NegotiationThread.tsx
    admin/
      AgentView.tsx           # agent activity feed with tool badges, /admin route

eval/
  gliner_vs_gemini.py         # Pioneer eval table: accuracy / latency / cost
```

---

## ⚡ Do This First (parallel with Task 1)

Before writing any code, kick off Pioneer fine-tuning — it takes time to run in the background.

Log into the Pioneer by Fastino dashboard and submit this task description:
> "Extract structured information from second-hand marketplace listings in German and English. Schema: brand (string), model (string), condition ('new'|'like_new'|'very_good'|'good'|'acceptable'), price_eur (float), location_city (string), defects (list of strings). Also classify negotiation messages into one of: initial_offer, counter_offer, accept, reject, question, stall."

Save the resulting endpoint URL as `PIONEER_ENDPOINT` in your `.env`. The fine-tuned model will be ready while you build the rest of the backend.

---

## Phase 1 — Foundation

### Task 1: Backend project setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "buybot-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "langgraph>=0.2.0",
  "langchain-google-genai>=1.0.0",
  "fastapi>=0.111.0",
  "uvicorn[standard]>=0.29.0",
  "tavily-python>=0.3.0",
  "gliner>=0.2.0",
  "httpx>=0.27.0",
  "pydantic>=2.0.0",
  "python-dotenv>=1.0.0",
  "pytest>=8.0.0",
  "pytest-asyncio>=0.23.0",
  "httpx[test]>=0.27.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create `.env.example`**

```
GEMINI_API_KEY=your_gemini_key_here
TAVILY_API_KEY=your_tavily_key_here
GOOGLE_MAPS_API_KEY=your_maps_key_here
PIONEER_ENDPOINT=https://api.fastino.ai/v1/infer/YOUR_MODEL_ID
```

- [ ] **Step 3: Install deps and verify**

```bash
cd backend
pip install -e .
python -c "import langgraph, fastapi, gliner; print('OK')"
```
Expected output: `OK`

- [ ] **Step 4: Create empty `app/__init__.py`**

```python
```

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: backend project scaffold"
```

---

### Task 2: Frontend project setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Scaffold with Vite**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npm install react-router-dom
npx tailwindcss init -p
```

- [ ] **Step 2: Configure `tailwind.config.ts`**

```ts
import type { Config } from 'tailwindcss'
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
} satisfies Config
```

- [ ] **Step 3: Add Tailwind directives to `src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Replace `src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 5: Create placeholder `src/App.tsx`**

```tsx
export default function App() {
  return <div className="min-h-screen bg-slate-900 text-white p-8">BuyBot loading...</div>
}
```

- [ ] **Step 6: Verify dev server starts**

```bash
npm run dev
```
Expected: server at http://localhost:5173 with white text on dark background.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: frontend project scaffold"
```

---

## Phase 2 — Core Types & Mock Data

### Task 3: State types

**Files:**
- Create: `backend/app/state.py`
- Create: `backend/tests/test_state.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_state.py`:

```python
from app.state import ProcurementState, PendingDecision, NegotiationMessage, initial_state

def test_initial_state_has_required_keys():
    s = initial_state("iPhone 14", 200.0, "good+", "München", 15)
    assert s["query"] == "iPhone 14"
    assert s["budget"] == 200.0
    assert s["status"] == "searching"
    assert s["degraded"] == []
    assert s["decision_history"] == []
    assert s["current_candidate_index"] == 0
    assert s["confirmed"] is False
    assert s["pending_decision"] is None
    assert s["final_price"] is None

def test_pending_decision_has_required_fields():
    pd: PendingDecision = {
        "checkpoint": "confirm_candidate",
        "summary": "Found iPhone 14 at €175",
        "options": [{"id": "approve", "label": "Go for it"}],
        "context": {}
    }
    assert pd["checkpoint"] == "confirm_candidate"

def test_negotiation_message_has_required_fields():
    msg: NegotiationMessage = {
        "role": "buyer",
        "text": "I offer €160",
        "act": "initial_offer",
        "price": 160.0,
        "ts": "2026-06-13T10:00:00"
    }
    assert msg["act"] == "initial_offer"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_state.py -v
```
Expected: `ImportError` — module not found yet.

- [ ] **Step 3: Create `app/state.py`**

```python
from __future__ import annotations
from typing import Literal, TypedDict

class PendingDecision(TypedDict):
    checkpoint: str
    summary: str
    options: list[dict]
    context: dict

class NegotiationMessage(TypedDict):
    role: Literal["buyer", "seller"]
    text: str
    act: Literal["initial_offer", "counter_offer", "accept", "reject", "question", "stall"]
    price: float | None
    ts: str

class ProcurementState(TypedDict):
    # Input
    query: str
    budget: float
    condition: str
    location: str
    max_distance_km: int
    # Search
    raw_listings: list[dict]
    structured_listings: list[dict]
    # Analysis
    ranked_candidates: list[dict]
    current_candidate_index: int
    # Negotiation
    negotiation_thread: list[NegotiationMessage]
    final_price: float | None
    # Coordination
    meetup_proposal: dict | None
    confirmed: bool
    # Human-in-the-loop
    pending_decision: PendingDecision | None
    decision_history: list[dict]
    human_feedback: str | None
    # Control
    status: Literal[
        "searching", "reviewing", "awaiting_human",
        "negotiating", "coordinating", "done", "failed"
    ]
    degraded: list[str]

def initial_state(
    query: str, budget: float, condition: str, location: str, max_distance_km: int
) -> ProcurementState:
    return {
        "query": query, "budget": budget, "condition": condition,
        "location": location, "max_distance_km": max_distance_km,
        "raw_listings": [], "structured_listings": [],
        "ranked_candidates": [], "current_candidate_index": 0,
        "negotiation_thread": [], "final_price": None,
        "meetup_proposal": None, "confirmed": False,
        "pending_decision": None, "decision_history": [],
        "human_feedback": None,
        "status": "searching", "degraded": [],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/state.py backend/tests/test_state.py
git commit -m "feat: core state types + initial_state factory"
```

---

### Task 4: Mock data

**Files:**
- Create: `backend/app/mock/listings.py`
- Create: `backend/app/mock/seller.py`
- Create: `backend/app/mock/__init__.py`

- [ ] **Step 1: Create `app/mock/__init__.py`** (empty)

- [ ] **Step 2: Create `app/mock/listings.py`**

```python
"""Pre-prepared listing data for FB Marketplace (always mock) and Vinted fallback."""

FACEBOOK_LISTINGS = [
    {
        "platform": "facebook",
        "title": "iPhone 14 128GB Space Grey — top condition",
        "price_text": "€185",
        "location": "Schwabing, München",
        "url": "https://www.facebook.com/marketplace/item/mock-001",
        "seller_rating": 4.7,
        "seller_reviews": 18,
        "raw_description": "iPhone 14 128GB Space Grey. Sehr guter Zustand, keine Kratzer. Original-Verpackung vorhanden. Akku 94%.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 Pro 256GB Deep Purple",
        "price_text": "€350",
        "location": "Maxvorstadt, München",
        "url": "https://www.facebook.com/marketplace/item/mock-002",
        "seller_rating": 4.2,
        "seller_reviews": 5,
        "raw_description": "iPhone 14 Pro 256GB Deep Purple. Gut erhalten. Kleiner Kratzer auf der Rückseite.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 128GB Starlight",
        "price_text": "€170",
        "location": "Pasing, München",
        "url": "https://www.facebook.com/marketplace/item/mock-003",
        "seller_rating": 3.8,
        "seller_reviews": 3,
        "raw_description": "iPhone 14 128GB Starlight. Gebraucht, aber funktioniert einwandfrei. Ein paar kleine Gebrauchsspuren.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 128GB Midnight — wie neu",
        "price_text": "€195",
        "location": "Bogenhausen, München",
        "url": "https://www.facebook.com/marketplace/item/mock-004",
        "seller_rating": 4.9,
        "seller_reviews": 42,
        "raw_description": "iPhone 14 128GB Midnight. Wie neu, 2 Monate alt. Mit Hülle und Original-Kabel.",
    },
    {
        "platform": "facebook",
        "title": "iPhone 14 256GB Blue — guter Zustand",
        "price_text": "€210",
        "location": "Sendling, München",
        "url": "https://www.facebook.com/marketplace/item/mock-005",
        "seller_rating": 4.5,
        "seller_reviews": 11,
        "raw_description": "iPhone 14 256GB Blue. Guter Zustand. Displayschutz drauf seit Tag 1.",
    },
]

VINTED_FALLBACK_LISTINGS = [
    {
        "platform": "vinted",
        "title": "iPhone 14 128GB – sehr gut",
        "price_text": "€180",
        "location": "München",
        "url": "https://www.vinted.de/items/mock-v001",
        "seller_rating": 5.0,
        "seller_reviews": 67,
        "raw_description": "iPhone 14 128GB sehr guter Zustand. Akku 91%. Mit Originalzubehör.",
    },
    {
        "platform": "vinted",
        "title": "iPhone 14 Pro 128GB",
        "price_text": "€320",
        "location": "München Ost",
        "url": "https://www.vinted.de/items/mock-v002",
        "seller_rating": 4.6,
        "seller_reviews": 23,
        "raw_description": "iPhone 14 Pro 128GB Space Black. Normale Gebrauchsspuren.",
    },
]
```

- [ ] **Step 3: Create `app/mock/seller.py`**

```python
"""Deterministic mock seller that simulates counter-offer / accept / reject."""
import datetime

def mock_seller_response(listing_price: float, buyer_offer: float) -> dict:
    """
    Returns a NegotiationMessage dict simulating a seller reply.
    - offer >= 95% of listing_price  → accept
    - offer >= 82% of listing_price  → counter at listing_price * 0.92
    - offer <  82% of listing_price  → reject
    """
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if buyer_offer >= listing_price * 0.95:
        return {
            "role": "seller",
            "text": f"OK, einverstanden. €{buyer_offer:.0f} ist gut für mich.",
            "act": "accept",
            "price": buyer_offer,
            "ts": ts,
        }
    elif buyer_offer >= listing_price * 0.82:
        counter = round(listing_price * 0.92)
        return {
            "role": "seller",
            "text": f"Hmm, €{buyer_offer:.0f} ist etwas wenig. Ich mache es für €{counter}.",
            "act": "counter_offer",
            "price": float(counter),
            "ts": ts,
        }
    else:
        return {
            "role": "seller",
            "text": f"Tut mir leid, €{buyer_offer:.0f} ist zu wenig. Preis ist fest.",
            "act": "reject",
            "price": None,
            "ts": ts,
        }
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/mock/
git commit -m "feat: mock listing data and deterministic seller simulator"
```

---

## Phase 3 — Agents

### Task 5: Search Agent

**Files:**
- Create: `backend/app/agents/search.py`
- Create: `backend/app/agents/__init__.py`
- Create: `backend/tests/test_search.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_search.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.agents.search import search_node
from app.state import initial_state

def test_search_node_uses_mock_fallback_when_tavily_raises():
    state = initial_state("iPhone 14", 200.0, "good+", "München", 15)

    with patch("app.agents.search.TavilyClient") as MockClient:
        MockClient.return_value.search.side_effect = Exception("quota exceeded")
        result = search_node(state)

    assert len(result["raw_listings"]) > 0
    assert "tavily_fallback_to_mock" in result["degraded"]
    assert result["status"] == "reviewing"

def test_search_node_returns_listings_on_success():
    state = initial_state("iPhone 14", 200.0, "good+", "München", 15)
    fake_results = {"results": [{"title": "iPhone 14", "content": "€180 München"}]}

    with patch("app.agents.search.TavilyClient") as MockClient:
        MockClient.return_value.search.return_value = fake_results
        result = search_node(state)

    assert len(result["raw_listings"]) > 0
    assert "tavily_fallback_to_mock" not in result["degraded"]
    assert result["status"] == "reviewing"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_search.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `app/agents/__init__.py`** (empty)

- [ ] **Step 4: Create `app/agents/search.py`**

```python
import os
from tavily import TavilyClient
from app.state import ProcurementState
from app.mock.listings import FACEBOOK_LISTINGS, VINTED_FALLBACK_LISTINGS

def _build_queries(state: ProcurementState) -> list[str]:
    q = state["query"]
    loc = state["location"]
    return [
        f"{q} {loc} site:kleinanzeigen.de",
        f"{q} {loc} site:vinted.de",
    ]

def search_node(state: ProcurementState) -> dict:
    listings: list[dict] = []
    degraded = list(state.get("degraded", []))

    try:
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        for query in _build_queries(state):
            resp = client.search(query=query, max_results=10, search_depth="advanced")
            for r in resp.get("results", []):
                listings.append({
                    "platform": "kleinanzeigen" if "kleinanzeigen" in query else "vinted",
                    "title": r.get("title", ""),
                    "raw_description": r.get("content", ""),
                    "url": r.get("url", ""),
                    "price_text": "",   # GLiNER2 will extract
                    "location": state["location"],
                    "seller_rating": None,
                    "seller_reviews": None,
                })
    except Exception:
        degraded.append("tavily_fallback_to_mock")
        listings = FACEBOOK_LISTINGS + VINTED_FALLBACK_LISTINGS

    # Always add FB mock listings (unavailable via scraping)
    if "tavily_fallback_to_mock" not in degraded:
        listings += FACEBOOK_LISTINGS

    return {
        "raw_listings": listings,
        "degraded": degraded,
        "status": "reviewing",
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_search.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/ backend/tests/test_search.py
git commit -m "feat: search agent with Tavily + mock fallback"
```

---

### Task 6: Extract Agent

**Files:**
- Create: `backend/app/agents/extract.py`
- Create: `backend/tests/test_extract.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_extract.py`:

```python
import pytest
from unittest.mock import patch
from app.agents.extract import extract_listing, classify_message

def test_extract_listing_returns_required_fields():
    sample = "iPhone 14 128GB Space Grey. Sehr guter Zustand. €175. München Schwabing."
    with patch("app.agents.extract._call_pioneer") as mock_pioneer:
        mock_pioneer.return_value = {
            "brand": "Apple", "model": "iPhone 14 128GB Space Grey",
            "condition": "very_good", "price_eur": 175.0,
            "location_city": "München", "defects": []
        }
        result = extract_listing(sample)

    assert result["price_eur"] == 175.0
    assert result["condition"] == "very_good"
    assert "brand" in result

def test_classify_message_returns_valid_act():
    with patch("app.agents.extract._call_pioneer") as mock_pioneer:
        mock_pioneer.return_value = {"act": "counter_offer", "price": 160.0}
        result = classify_message("Ich mache es für €160.")

    assert result["act"] == "counter_offer"

def test_extract_listing_falls_back_to_gemini_on_pioneer_failure():
    sample = "iPhone 14 €175 München"
    with patch("app.agents.extract._call_pioneer", side_effect=Exception("timeout")):
        with patch("app.agents.extract._call_gemini_extract") as mock_gemini:
            mock_gemini.return_value = {
                "brand": "Apple", "model": "iPhone 14", "condition": "good",
                "price_eur": 175.0, "location_city": "München", "defects": []
            }
            result = extract_listing(sample, record_degraded=[])

    assert result["price_eur"] == 175.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extract.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `app/agents/extract.py`**

```python
import os, json, httpx, datetime
import google.generativeai as genai
from app.state import ProcurementState

_LISTING_SCHEMA = """Extract from this second-hand listing. Return JSON only, no markdown:
{"brand": str, "model": str, "condition": "new"|"like_new"|"very_good"|"good"|"acceptable",
 "price_eur": float|null, "location_city": str, "defects": [str]}
Listing: """

_MSG_SCHEMA = """Classify this negotiation message. Return JSON only:
{"act": "initial_offer"|"counter_offer"|"accept"|"reject"|"question"|"stall", "price": float|null}
Message: """

def _call_pioneer(prompt: str) -> dict:
    endpoint = os.environ["PIONEER_ENDPOINT"]
    resp = httpx.post(endpoint, json={"prompt": prompt}, timeout=5.0)
    resp.raise_for_status()
    return resp.json()

def _call_gemini_extract(prompt: str) -> dict:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    result = model.generate_content(prompt)
    text = result.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def extract_listing(raw_text: str, record_degraded: list | None = None) -> dict:
    prompt = _LISTING_SCHEMA + raw_text
    try:
        return _call_pioneer(prompt)
    except Exception:
        if record_degraded is not None:
            record_degraded.append("gliner2_fallback_to_gemini")
        return _call_gemini_extract(prompt)

def classify_message(text: str, record_degraded: list | None = None) -> dict:
    prompt = _MSG_SCHEMA + text
    try:
        return _call_pioneer(prompt)
    except Exception:
        if record_degraded is not None:
            record_degraded.append("gliner2_fallback_to_gemini")
        return _call_gemini_extract(prompt)

def extract_node(state: ProcurementState) -> dict:
    degraded = list(state.get("degraded", []))
    structured = []
    for listing in state["raw_listings"]:
        raw = f"{listing.get('title', '')} {listing.get('raw_description', '')} {listing.get('price_text', '')}"
        extracted = extract_listing(raw, record_degraded=degraded)
        structured.append({**listing, **extracted})
    return {
        "structured_listings": structured,
        "degraded": list(set(degraded)),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extract.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/extract.py backend/tests/test_extract.py
git commit -m "feat: extract agent — GLiNER2 via Pioneer with Gemini fallback"
```

---

### Task 7: Analyst Agent

**Files:**
- Create: `backend/app/agents/analyst.py`
- Create: `backend/tests/test_analyst.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_analyst.py`:

```python
from app.agents.analyst import score_listing, rank_candidates

def test_score_listing_prefers_lower_price():
    cheap = {"price_eur": 150.0, "condition": "very_good", "seller_rating": 4.5,
             "seller_reviews": 10, "distance_km": 3.0}
    expensive = {"price_eur": 200.0, "condition": "very_good", "seller_rating": 4.5,
                 "seller_reviews": 10, "distance_km": 3.0}
    assert score_listing(cheap, budget=200.0) > score_listing(expensive, budget=200.0)

def test_score_listing_penalises_poor_condition():
    good = {"price_eur": 175.0, "condition": "very_good", "seller_rating": 4.5,
            "seller_reviews": 10, "distance_km": 3.0}
    bad = {"price_eur": 175.0, "condition": "acceptable", "seller_rating": 4.5,
           "seller_reviews": 10, "distance_km": 3.0}
    assert score_listing(good, budget=200.0) > score_listing(bad, budget=200.0)

def test_rank_candidates_returns_sorted_list():
    listings = [
        {"price_eur": 200.0, "condition": "good", "seller_rating": 4.0,
         "seller_reviews": 5, "distance_km": 2.0},
        {"price_eur": 160.0, "condition": "very_good", "seller_rating": 4.8,
         "seller_reviews": 20, "distance_km": 5.0},
    ]
    ranked = rank_candidates(listings, budget=200.0)
    assert ranked[0]["price_eur"] == 160.0   # better deal should rank first
    assert all("score" in r for r in ranked)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_analyst.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `app/agents/analyst.py`**

```python
import os, json
import google.generativeai as genai
from app.state import ProcurementState, PendingDecision

_CONDITION_SCORE = {
    "new": 1.0, "like_new": 0.95, "very_good": 0.85,
    "good": 0.70, "acceptable": 0.50,
}

def score_listing(listing: dict, budget: float) -> float:
    price = listing.get("price_eur") or budget
    price_score = max(0.0, (budget - price) / budget)
    condition_score = _CONDITION_SCORE.get(listing.get("condition", "good"), 0.5)
    rating = listing.get("seller_rating") or 3.0
    reviews = min(listing.get("seller_reviews") or 0, 50)
    trust_score = (rating / 5.0) * 0.7 + (reviews / 50) * 0.3
    dist = listing.get("distance_km") or 15.0
    distance_score = max(0.0, 1.0 - dist / 20.0)
    return (price_score * 0.40 + condition_score * 0.30 +
            trust_score * 0.20 + distance_score * 0.10)

def rank_candidates(listings: list[dict], budget: float) -> list[dict]:
    scored = [{**l, "score": round(score_listing(l, budget) * 100)} for l in listings]
    return sorted(scored, key=lambda x: x["score"], reverse=True)

def _gemini_insight(candidate: dict, budget: float) -> str:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        f"You are a buyer's agent. In one short sentence (max 15 words), explain why "
        f"this listing is a good or bad deal. Budget: €{budget}. "
        f"Listing: {json.dumps(candidate)}"
    )
    return model.generate_content(prompt).text.strip()

def analyst_node(state: ProcurementState) -> dict:
    in_budget = [
        l for l in state["structured_listings"]
        if (l.get("price_eur") or 0) <= state["budget"]
    ]
    ranked = rank_candidates(in_budget, state["budget"])[:5]

    top = ranked[0] if ranked else {}
    insight = _gemini_insight(top, state["budget"]) if top else "No matching listings found."

    ranked[0]["insight"] = insight if ranked else None

    pending: PendingDecision = {
        "checkpoint": "confirm_candidate",
        "summary": f"Found {state['query']} from €{top.get('price_eur', '?')} — start negotiating?",
        "options": [
            {"id": "approve", "label": "Yes, go for #1"},
            {"id": "pick_2", "label": "Show me #2 instead"},
            {"id": "cancel", "label": "Cancel search"},
        ],
        "context": {"ranked_candidates": ranked},
    }
    return {
        "ranked_candidates": ranked,
        "pending_decision": pending,
        "status": "awaiting_human",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_analyst.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/analyst.py backend/tests/test_analyst.py
git commit -m "feat: analyst agent — scoring, ranking, Gemini insight"
```

---

### Task 8: Negotiation Agent

**Files:**
- Create: `backend/app/agents/negotiate.py`

- [ ] **Step 1: Create `app/agents/negotiate.py`**

```python
import os, json, datetime
import google.generativeai as genai
from langgraph.types import interrupt
from app.state import ProcurementState, PendingDecision, NegotiationMessage
from app.agents.extract import classify_message
from app.mock.seller import mock_seller_response

def _gemini_opening_offer(listing: dict, budget: float) -> dict:
    """Returns {offer_price: float, message_text: str}"""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    listing_price = listing.get("price_eur", budget)
    prompt = (
        f"You are a buyer's agent negotiating in German. "
        f"Listing price: €{listing_price}. Your max budget: €{budget}. "
        f"Suggest a strategic opening offer (80-90% of listing price) and write a polite German message. "
        f"Return JSON only: {{\"offer_price\": float, \"message_text\": str}}"
    )
    text = model.generate_content(prompt).text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def _gemini_counter_response(thread: list, budget: float, seller_price: float) -> dict:
    """Returns {offer_price: float, message_text: str, recommendation: str}"""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    history = "\n".join([f"{m['role']}: {m['text']}" for m in thread[-4:]])
    prompt = (
        f"Seller countered at €{seller_price}. Budget: €{budget}. "
        f"Recent messages:\n{history}\n"
        f"Recommend: accept, counter at X, or walk away? "
        f"Return JSON: {{\"offer_price\": float|null, \"message_text\": str, "
        f"\"recommendation\": \"accept\"|\"counter\"|\"walk_away\"}}"
    )
    text = model.generate_content(prompt).text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def negotiate_node(state: ProcurementState) -> dict:
    degraded = list(state.get("degraded", []))
    idx = state["current_candidate_index"]
    candidates = state["ranked_candidates"]

    if idx >= len(candidates):
        return {"status": "failed", "degraded": degraded}

    listing = candidates[idx]
    listing_price = listing.get("price_eur", state["budget"])
    thread = list(state.get("negotiation_thread", []))
    ts = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

    # --- Round 1: opening offer ---
    if not thread:
        offer_data = _gemini_opening_offer(listing, state["budget"])
        offer_price = offer_data["offer_price"]
        buyer_msg: NegotiationMessage = {
            "role": "buyer", "text": offer_data["message_text"],
            "act": "initial_offer", "price": offer_price, "ts": ts()
        }
        thread.append(buyer_msg)

        pending: PendingDecision = {
            "checkpoint": "confirm_offer",
            "summary": f"Opening offer: €{offer_price:.0f} to seller (listed at €{listing_price:.0f}). Send?",
            "options": [
                {"id": "approve", "label": f"Send €{offer_price:.0f}"},
                {"id": "lower", "label": "Go lower"},
                {"id": "skip", "label": "Skip this seller"},
            ],
            "context": {"offer_price": offer_price, "listing_price": listing_price},
        }
        choice = interrupt(pending)
        decision_entry = {"checkpoint": "confirm_offer", "choice": choice, "ts": ts()}

        if choice == "skip":
            return {
                "negotiation_thread": [],
                "current_candidate_index": idx + 1,
                "decision_history": state["decision_history"] + [decision_entry],
                "status": "negotiating",
            }
        if choice == "lower":
            offer_price = round(listing_price * 0.78)
            thread[-1] = {**thread[-1], "price": float(offer_price),
                          "text": f"Würden Sie €{offer_price:.0f} akzeptieren?"}

        # Simulate seller response
        seller_reply = mock_seller_response(listing_price, offer_price)
        classified = classify_message(seller_reply["text"], record_degraded=degraded)
        seller_reply = {**seller_reply, "act": classified["act"],
                        "price": classified.get("price") or seller_reply.get("price")}
        thread.append(seller_reply)

        if seller_reply["act"] == "accept":
            return {
                "negotiation_thread": thread,
                "final_price": offer_price,
                "decision_history": state["decision_history"] + [decision_entry],
                "degraded": list(set(degraded)),
                "status": "coordinating",
            }

    # --- Round 2: handle counter-offer ---
    last_seller = next((m for m in reversed(thread) if m["role"] == "seller"), None)
    if not last_seller or last_seller["act"] in ("accept",):
        return {"negotiation_thread": thread, "status": "coordinating",
                "final_price": state.get("final_price"), "degraded": list(set(degraded))}

    if last_seller["act"] == "reject":
        return {"negotiation_thread": thread, "negotiation_thread": [],
                "current_candidate_index": idx + 1, "status": "negotiating",
                "degraded": list(set(degraded))}

    seller_price = last_seller.get("price") or listing_price
    counter_data = _gemini_counter_response(thread, state["budget"], seller_price)

    pending2: PendingDecision = {
        "checkpoint": "confirm_offer",
        "summary": (f"Seller countered at €{seller_price:.0f}. "
                    f"Agent recommends: {counter_data['recommendation']}"),
        "options": [
            {"id": "accept", "label": f"Accept €{seller_price:.0f}"},
            {"id": "counter", "label": f"Counter at €{counter_data.get('offer_price', seller_price - 5):.0f}"},
            {"id": "skip", "label": "Walk away"},
        ],
        "context": {"seller_price": seller_price, "counter_data": counter_data},
    }
    choice2 = interrupt(pending2)
    decision_entry2 = {"checkpoint": "confirm_offer", "choice": choice2, "ts": ts()}

    if choice2 == "accept":
        return {
            "negotiation_thread": thread,
            "final_price": seller_price,
            "decision_history": state["decision_history"] + [decision_entry2],
            "degraded": list(set(degraded)),
            "status": "coordinating",
        }
    if choice2 == "skip":
        return {
            "negotiation_thread": [],
            "current_candidate_index": idx + 1,
            "decision_history": state["decision_history"] + [decision_entry2],
            "status": "negotiating",
        }

    # Counter offer
    counter_price = counter_data.get("offer_price") or seller_price - 5
    buyer_counter: NegotiationMessage = {
        "role": "buyer", "text": counter_data["message_text"],
        "act": "counter_offer", "price": float(counter_price), "ts": ts()
    }
    thread.append(buyer_counter)
    seller_final = mock_seller_response(listing_price, counter_price)
    thread.append(seller_final)
    final_price = counter_price if seller_final["act"] == "accept" else seller_price

    return {
        "negotiation_thread": thread,
        "final_price": float(final_price),
        "decision_history": state["decision_history"] + [decision_entry2],
        "degraded": list(set(degraded)),
        "status": "coordinating",
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/agents/negotiate.py
git commit -m "feat: negotiation agent — Gemini strategy + interrupt() checkpoints"
```

---

### Task 9: Coordination Agent

**Files:**
- Create: `backend/app/agents/coordinate.py`

- [ ] **Step 1: Create `app/agents/coordinate.py`**

```python
import os, json, datetime
import httpx
import google.generativeai as genai
from langgraph.types import interrupt
from app.state import ProcurementState, PendingDecision

def _get_travel_time(origin: str, destination: str) -> dict:
    """Returns {duration_text: str, duration_seconds: int, mode: str}"""
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not key:
        return {"duration_text": "~15 min", "duration_seconds": 900, "mode": "transit"}
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {"origin": origin, "destination": destination,
              "mode": "transit", "key": key}
    try:
        resp = httpx.get(url, params=params, timeout=5.0)
        data = resp.json()
        leg = data["routes"][0]["legs"][0]
        return {
            "duration_text": leg["duration"]["text"],
            "duration_seconds": leg["duration"]["value"],
            "mode": "transit",
        }
    except Exception:
        return {"duration_text": "~15 min", "duration_seconds": 900, "mode": "transit"}

def _gemini_meetup_proposal(buyer_location: str, seller_location: str,
                             buyer_route: dict, final_price: float) -> dict:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        f"Suggest a convenient public meetup location between '{buyer_location}' and "
        f"'{seller_location}' in München (a Bahnhof, Marktplatz, or well-known landmark). "
        f"Also suggest a time (weekday afternoon or weekend). "
        f"Return JSON: {{\"location\": str, \"time_suggestion\": str, \"reason\": str}}"
    )
    text = model.generate_content(prompt).text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def coordinate_node(state: ProcurementState) -> dict:
    idx = state["current_candidate_index"]
    listing = state["ranked_candidates"][idx]
    final_price = state.get("final_price") or listing.get("price_eur", 0)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    buyer_location = state["location"]
    seller_location = listing.get("location_city") or listing.get("location", "München")

    buyer_route = _get_travel_time(buyer_location, seller_location)
    meetup_data = _gemini_meetup_proposal(
        buyer_location, seller_location, buyer_route, final_price
    )

    meetup_proposal = {
        "location": meetup_data["location"],
        "time_suggestion": meetup_data["time_suggestion"],
        "reason": meetup_data["reason"],
        "buyer_route": buyer_route,
        "seller_location": seller_location,
        "final_price": final_price,
    }

    pending: PendingDecision = {
        "checkpoint": "confirm_meetup",
        "summary": (f"Meet at {meetup_data['location']} — "
                    f"{meetup_data['time_suggestion']} ({buyer_route['duration_text']} away). Confirm?"),
        "options": [
            {"id": "confirm", "label": "Confirm meetup"},
            {"id": "reschedule", "label": "Suggest different time"},
            {"id": "cancel", "label": "Cancel"},
        ],
        "context": {"meetup_proposal": meetup_proposal},
    }
    choice = interrupt(pending)
    decision_entry = {"checkpoint": "confirm_meetup", "choice": choice, "ts": ts}

    if choice == "cancel":
        return {
            "status": "failed",
            "decision_history": state["decision_history"] + [decision_entry],
        }

    return {
        "meetup_proposal": meetup_proposal,
        "confirmed": True,
        "pending_decision": None,
        "decision_history": state["decision_history"] + [decision_entry],
        "status": "done",
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/agents/coordinate.py
git commit -m "feat: coordination agent — Google Maps routes + Gemini meetup proposal"
```

---

## Phase 4 — LangGraph Graph

### Task 10: Graph definition + session management

**Files:**
- Create: `backend/app/graph.py`
- Create: `backend/app/sessions.py`

- [ ] **Step 1: Create `app/sessions.py`**

```python
import asyncio
from collections import defaultdict

# session_id → list of WebSocket send callbacks
_ws_listeners: dict[str, list] = defaultdict(list)
# session_id → list of activity log events
_activity_logs: dict[str, list] = {}

def register_ws(session_id: str, send_fn) -> None:
    _ws_listeners[session_id].append(send_fn)

def unregister_ws(session_id: str, send_fn) -> None:
    _ws_listeners[session_id] = [
        f for f in _ws_listeners[session_id] if f is not send_fn
    ]

async def broadcast(session_id: str, event: dict) -> None:
    _activity_logs.setdefault(session_id, []).append(event)
    dead = []
    for send_fn in _ws_listeners.get(session_id, []):
        try:
            await send_fn(event)
        except Exception:
            dead.append(send_fn)
    for fn in dead:
        unregister_ws(session_id, fn)

def get_logs(session_id: str) -> list:
    return _activity_logs.get(session_id, [])
```

- [ ] **Step 2: Create `app/graph.py`**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.state import ProcurementState
from app.agents.search import search_node
from app.agents.extract import extract_node
from app.agents.analyst import analyst_node
from app.agents.negotiate import negotiate_node
from app.agents.coordinate import coordinate_node

def _should_continue_negotiating(state: ProcurementState) -> str:
    if state["status"] == "failed":
        return END
    if state["status"] == "coordinating":
        return "coordinate"
    return "negotiate"

def build_graph() -> tuple:
    builder = StateGraph(ProcurementState)
    builder.add_node("search", search_node)
    builder.add_node("extract", extract_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("negotiate", negotiate_node)
    builder.add_node("coordinate", coordinate_node)

    builder.set_entry_point("search")
    builder.add_edge("search", "extract")
    builder.add_edge("extract", "analyst")
    builder.add_edge("analyst", "negotiate")
    builder.add_conditional_edges(
        "negotiate",
        _should_continue_negotiating,
        {"negotiate": "negotiate", "coordinate": "coordinate", END: END},
    )
    builder.add_edge("coordinate", END)

    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory, interrupt_before=["negotiate", "coordinate"])
    return graph, memory

_graph, _memory = build_graph()

def get_graph():
    return _graph
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/graph.py backend/app/sessions.py
git commit -m "feat: LangGraph graph — 5-node pipeline with MemorySaver"
```

---

## Phase 5 — API Layer

### Task 11: FastAPI routes + WebSocket

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing API test**

Create `backend/tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_post_session_returns_session_id():
    with patch("app.main.get_graph") as mock_graph:
        mock_graph.return_value.invoke.return_value = {
            "status": "awaiting_human",
            "pending_decision": {
                "checkpoint": "confirm_candidate",
                "summary": "Found iPhone",
                "options": [{"id": "approve", "label": "Yes"}],
                "context": {}
            },
            "degraded": [],
        }
        from app.main import app
        client = TestClient(app)
        resp = client.post("/session", json={
            "query": "iPhone 14", "budget": 200.0,
            "condition": "good+", "location": "München", "max_distance_km": 15
        })
    assert resp.status_code == 200
    assert "session_id" in resp.json()

def test_get_state_returns_404_for_unknown_session():
    from app.main import app
    client = TestClient(app)
    resp = client.get("/session/nonexistent/state")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_api.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `app/main.py`**

```python
import uuid, asyncio, os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command

from app.graph import get_graph
from app.state import initial_state
from app.sessions import register_ws, unregister_ws, broadcast, get_logs

app = FastAPI(title="BuyBot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

_sessions: dict[str, dict] = {}   # session_id → {thread_id, last_state}

class SessionRequest(BaseModel):
    query: str
    budget: float
    condition: str = "good+"
    location: str
    max_distance_km: int = 15

class FeedbackRequest(BaseModel):
    choice: str
    free_text: str | None = None

def _run_graph(thread_id: str, input_or_command, session_id: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.invoke(input_or_command, config=config)
    _sessions[session_id]["last_state"] = state
    agent_name = {
        "searching": "search", "reviewing": "extract",
        "awaiting_human": "analyst", "negotiating": "negotiate",
        "coordinating": "coordinate", "done": "coordinate", "failed": "orchestrator",
    }.get(state.get("status", ""), "orchestrator")
    asyncio.create_task(broadcast(session_id, {
        "event": "state_changed",
        "status": state.get("status"),
    }))
    asyncio.create_task(broadcast(session_id, {
        "event": "agent_log",
        "agent": agent_name,
        "msg": f"Status: {state.get('status')}. Degraded: {state.get('degraded', [])}",
    }))
    return state

@app.post("/session")
async def create_session(req: SessionRequest):
    session_id = str(uuid.uuid4())
    thread_id = session_id
    _sessions[session_id] = {"thread_id": thread_id, "last_state": None}

    state = initial_state(req.query, req.budget, req.condition, req.location, req.max_distance_km)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_graph, thread_id, state, session_id)
    return {"session_id": session_id}

@app.get("/session/{session_id}/state")
async def get_state(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]["last_state"]

@app.post("/session/{session_id}/feedback")
async def post_feedback(session_id: str, req: FeedbackRequest):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    thread_id = _sessions[session_id]["thread_id"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _run_graph, thread_id, Command(resume=req.choice), session_id
    )
    return {"ok": True}

@app.get("/session/{session_id}/result")
async def get_result(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    state = _sessions[session_id]["last_state"] or {}
    if state.get("status") != "done":
        raise HTTPException(status_code=400, detail="Session not complete")
    return state.get("meetup_proposal")

@app.websocket("/session/{session_id}/stream")
async def websocket_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    async def send_fn(event: dict):
        await websocket.send_json(event)
    register_ws(session_id, send_fn)
    # Send existing logs immediately
    for log in get_logs(session_id):
        await websocket.send_json(log)
    try:
        while True:
            await websocket.receive_text()   # keep alive
    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(session_id, send_fn)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_api.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Smoke-test the server manually**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# In another terminal:
curl -X POST http://localhost:8000/session \
  -H "Content-Type: application/json" \
  -d '{"query":"iPhone 14","budget":200,"location":"München","max_distance_km":15}'
```
Expected: JSON with `session_id`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_api.py
git commit -m "feat: FastAPI routes + WebSocket stream"
```

---

## Phase 6 — Frontend Foundation

### Task 12: API client + useSession hook

**Files:**
- Create: `frontend/src/api.ts`
- Create: `frontend/src/useSession.ts`

- [ ] **Step 1: Create `src/api.ts`**

```ts
const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface SessionState {
  query?: string
  budget?: number
  status?: string
  ranked_candidates?: Candidate[]
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
```

- [ ] **Step 2: Create `src/useSession.ts`**

```ts
import { useState, useEffect, useRef, useCallback } from 'react'
import { getState, postFeedback, connectWS, SessionState, WsEvent } from './api'

export interface AgentLogEntry {
  agent: string
  msg: string
  ts: number
}

export function useSession(sessionId: string | null) {
  const [state, setState] = useState<SessionState | null>(null)
  const [logs, setLogs] = useState<AgentLogEntry[]>([])
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    if (!sessionId) return
    const s = await getState(sessionId)
    setState(s)
  }, [sessionId])

  const sendFeedback = useCallback(async (choice: string, freeText?: string) => {
    if (!sessionId) return
    await postFeedback(sessionId, choice, freeText)
    await refresh()
  }, [sessionId, refresh])

  useEffect(() => {
    if (!sessionId) return
    refresh()
    pollRef.current = setInterval(refresh, 2000)

    const disconnect = connectWS(sessionId, (e: WsEvent) => {
      if (e.event === 'state_changed') refresh()
      if (e.event === 'agent_log') {
        setLogs(prev => [...prev, {
          agent: e.agent ?? 'system',
          msg: e.msg ?? '',
          ts: Date.now(),
        }])
      }
    })

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      disconnect()
    }
  }, [sessionId, refresh])

  return { state, logs, sendFeedback, refresh }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts frontend/src/useSession.ts
git commit -m "feat: API client + useSession hook with WS + polling"
```

---

### Task 13: App routing + InputScreen

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/screens/InputScreen.tsx`
- Create: `frontend/src/components/StepBar.tsx`

- [ ] **Step 1: Create `src/components/StepBar.tsx`**

```tsx
const STEPS = ['Search', 'Analyse', 'Choose', 'Negotiate', 'Meet up']

const STATUS_STEP: Record<string, number> = {
  searching: 0, reviewing: 1, awaiting_human: 2,
  negotiating: 3, coordinating: 4, done: 4,
}

export default function StepBar({ status }: { status?: string }) {
  const active = STATUS_STEP[status ?? 'searching'] ?? 0
  return (
    <div className="flex items-center justify-center gap-0 py-3">
      {STEPS.map((label, i) => (
        <div key={label} className="flex items-center">
          <div className="flex items-center gap-1.5">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
              ${i < active ? 'bg-indigo-500 text-white' :
                i === active ? 'bg-orange-500 text-white' :
                'bg-slate-200 text-slate-400'}`}>
              {i < active ? '✓' : i + 1}
            </div>
            <span className={`text-xs font-medium
              ${i < active ? 'text-indigo-600' :
                i === active ? 'text-orange-600 font-bold' :
                'text-slate-400'}`}>{label}</span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-6 h-0.5 mx-1 ${i < active ? 'bg-indigo-400' : 'bg-slate-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Create `src/screens/InputScreen.tsx`**

```tsx
import { useState } from 'react'
import { createSession } from '../api'

interface Props { onStart: (sessionId: string) => void }

export default function InputScreen({ onStart }: Props) {
  const [query, setQuery] = useState('')
  const [budget, setBudget] = useState(200)
  const [condition, setCondition] = useState('good+')
  const [location, setLocation] = useState('München')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!query.trim()) return
    setLoading(true)
    const id = await createSession({ query, budget, condition, location, max_distance_km: 15 })
    onStart(id)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <div className="text-2xl font-black text-indigo-600 tracking-tight mb-1">buybot</div>
        <div className="text-slate-500 text-sm mb-6">Tell me what you want to buy</div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">What are you looking for?</label>
            <input
              className="mt-1 w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              placeholder="e.g. iPhone 14, Sony A7III, MacBook Air..."
              value={query} onChange={e => setQuery(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Max budget: <span className="text-indigo-600">€{budget}</span>
            </label>
            <input type="range" min={50} max={2000} step={10} value={budget}
              onChange={e => setBudget(Number(e.target.value))}
              className="w-full mt-2 accent-indigo-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Minimum condition</label>
            <select value={condition} onChange={e => setCondition(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="acceptable">Acceptable</option>
              <option value="good">Good</option>
              <option value="good+">Good+</option>
              <option value="very_good">Very Good</option>
              <option value="like_new">Like New</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Your city</label>
            <input
              className="mt-1 w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              value={location} onChange={e => setLocation(e.target.value)}
            />
          </div>

          <button onClick={handleSubmit} disabled={loading || !query.trim()}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white
              font-bold py-4 rounded-xl transition-colors text-sm mt-2">
            {loading ? 'Starting agents...' : '🤖 Find me the best deal →'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create `src/App.tsx`**

```tsx
import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import InputScreen from './screens/InputScreen'
import ProcessingScreen from './screens/ProcessingScreen'
import ChooseScreen from './screens/ChooseScreen'
import NegotiateScreen from './screens/NegotiateScreen'
import MeetupScreen from './screens/MeetupScreen'
import DoneScreen from './screens/DoneScreen'
import AgentView from './admin/AgentView'
import { useSession } from './useSession'

function BuyerFlow() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const { state, logs, sendFeedback } = useSession(sessionId)

  if (!sessionId) return <InputScreen onStart={setSessionId} />

  const status = state?.status
  if (!status || status === 'searching' || status === 'reviewing') {
    return <ProcessingScreen status={status} />
  }
  if (status === 'awaiting_human') {
    const cp = state?.pending_decision?.checkpoint
    if (cp === 'confirm_candidate') return <ChooseScreen state={state} onFeedback={sendFeedback} />
    if (cp === 'confirm_offer') return <NegotiateScreen state={state} onFeedback={sendFeedback} />
    if (cp === 'confirm_meetup') return <MeetupScreen state={state} onFeedback={sendFeedback} />
  }
  if (status === 'negotiating' || status === 'coordinating') {
    return <ProcessingScreen status={status} />
  }
  if (status === 'done') return <DoneScreen state={state} />
  return <ProcessingScreen status={status} />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<BuyerFlow />} />
      <Route path="/admin" element={<AgentView />} />
    </Routes>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: App routing + InputScreen + StepBar"
```

---

### Task 14: ProcessingScreen + placeholder screens

**Files:**
- Create: `frontend/src/screens/ProcessingScreen.tsx`
- Create: `frontend/src/screens/ChooseScreen.tsx` (stub)
- Create: `frontend/src/screens/NegotiateScreen.tsx` (stub)
- Create: `frontend/src/screens/MeetupScreen.tsx` (stub)
- Create: `frontend/src/screens/DoneScreen.tsx` (stub)
- Create: `frontend/src/admin/AgentView.tsx` (stub)

- [ ] **Step 1: Create `src/screens/ProcessingScreen.tsx`**

```tsx
import StepBar from '../components/StepBar'

const STATUS_MSG: Record<string, string> = {
  searching: 'Searching across Kleinanzeigen, Vinted and more...',
  reviewing: 'Extracting and structuring listings...',
  negotiating: 'Negotiating with the seller...',
  coordinating: 'Planning your meetup...',
}

export default function ProcessingScreen({ status }: { status?: string }) {
  const msg = STATUS_MSG[status ?? 'searching'] ?? 'Working on it...'
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
        <div className="text-3xl mb-4 animate-bounce">🤖</div>
        <div className="text-lg font-bold text-slate-800 mb-2">Agents are working</div>
        <div className="text-sm text-slate-500 mb-6">{msg}</div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500 rounded-full animate-pulse w-3/4" />
        </div>
        <div className="mt-6">
          <StepBar status={status} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create stub screens** (will be filled in subsequent tasks)

Create `src/screens/ChooseScreen.tsx`:
```tsx
export default function ChooseScreen({ state, onFeedback }: any) {
  return <div className="p-8 text-center">ChooseScreen — coming in Task 15</div>
}
```

Create `src/screens/NegotiateScreen.tsx`:
```tsx
export default function NegotiateScreen({ state, onFeedback }: any) {
  return <div className="p-8 text-center">NegotiateScreen — coming in Task 16</div>
}
```

Create `src/screens/MeetupScreen.tsx`:
```tsx
export default function MeetupScreen({ state, onFeedback }: any) {
  return <div className="p-8 text-center">MeetupScreen — coming in Task 17</div>
}
```

Create `src/screens/DoneScreen.tsx`:
```tsx
export default function DoneScreen({ state }: any) {
  return <div className="p-8 text-center">DoneScreen — coming in Task 17</div>
}
```

Create `src/admin/AgentView.tsx`:
```tsx
export default function AgentView() {
  return <div className="p-8 text-center bg-slate-900 min-h-screen text-white">AgentView — coming in Task 18</div>
}
```

- [ ] **Step 3: Verify app compiles**

```bash
npm run build
```
Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/screens/ frontend/src/admin/
git commit -m "feat: ProcessingScreen + stub screens"
```

---

### Task 15: ChooseScreen (Human CP1)

**Files:**
- Modify: `frontend/src/screens/ChooseScreen.tsx`
- Create: `frontend/src/components/ListingCard.tsx`
- Create: `frontend/src/components/CheckpointBanner.tsx`

- [ ] **Step 1: Create `src/components/ListingCard.tsx`**

```tsx
import { Candidate } from '../api'

interface Props { candidate: Candidate; rank: number; selected?: boolean; onClick?: () => void }

const CONDITION_LABEL: Record<string, string> = {
  new: 'New', like_new: 'Like New', very_good: 'Very Good',
  good: 'Good', acceptable: 'Acceptable',
}

export default function ListingCard({ candidate, rank, selected, onClick }: Props) {
  return (
    <div onClick={onClick}
      className={`border-2 rounded-xl p-4 cursor-pointer transition-all
        ${selected ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300'}`}>
      <div className="flex gap-3">
        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black shrink-0
          ${rank === 0 ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500'}`}>
          {rank + 1}
        </div>
        <div className="text-2xl">📱</div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-800 text-sm truncate">{candidate.title}</div>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-xl font-black text-emerald-600">€{candidate.price_eur}</span>
            {candidate.score >= 85 && (
              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-semibold">
                Great deal
              </span>
            )}
          </div>
          <div className="flex gap-3 mt-1 text-xs text-slate-400 flex-wrap">
            {candidate.seller_rating && <span>⭐ {candidate.seller_rating}</span>}
            <span>📍 {candidate.location}</span>
            <span className="capitalize">{CONDITION_LABEL[candidate.condition] ?? candidate.condition}</span>
          </div>
          {candidate.insight && (
            <div className="mt-2 text-xs text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg">
              💡 {candidate.insight}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `src/components/CheckpointBanner.tsx`**

```tsx
import { PendingDecision } from '../api'

interface Props {
  decision: PendingDecision
  onChoice: (id: string) => void
  loading?: boolean
}

export default function CheckpointBanner({ decision, onChoice, loading }: Props) {
  return (
    <div className="bg-amber-50 border-t-2 border-amber-400 px-4 py-4">
      <div className="flex items-start gap-3 mb-3">
        <span className="text-2xl">🎯</span>
        <div>
          <div className="font-bold text-amber-900 text-sm">{decision.summary}</div>
        </div>
      </div>
      <div className="flex gap-2 flex-wrap">
        {decision.options.map(opt => (
          <button key={opt.id}
            disabled={loading}
            onClick={() => onChoice(opt.id)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors
              ${opt.id === decision.options[0].id
                ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Replace `src/screens/ChooseScreen.tsx`**

```tsx
import { useState } from 'react'
import { SessionState } from '../api'
import StepBar from '../components/StepBar'
import ListingCard from '../components/ListingCard'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props { state: SessionState; onFeedback: (choice: string) => Promise<void> }

export default function ChooseScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const candidates = state.ranked_candidates ?? []
  const decision = state.pending_decision!

  const handleChoice = async (choice: string) => {
    setLoading(true)
    await onFeedback(choice)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4">
      <div className="w-full max-w-md">
        <div className="text-xl font-black text-indigo-600 py-4">buybot</div>
        <StepBar status={state.status} />

        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mt-4">
          <div className="px-4 pt-4 pb-2">
            <div className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-3">
              Top results · {candidates.length} candidates
            </div>
            <div className="space-y-3">
              {candidates.slice(0, 3).map((c, i) => (
                <ListingCard key={i} candidate={c} rank={i} />
              ))}
            </div>
          </div>
          <CheckpointBanner decision={decision} onChoice={handleChoice} loading={loading} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: ChooseScreen (CP1) + ListingCard + CheckpointBanner components"
```

---

### Task 16: NegotiateScreen (Human CP2)

**Files:**
- Modify: `frontend/src/screens/NegotiateScreen.tsx`
- Create: `frontend/src/components/NegotiationThread.tsx`

- [ ] **Step 1: Create `src/components/NegotiationThread.tsx`**

```tsx
import { NegotiationMessage } from '../api'

const ACT_LABEL: Record<string, string> = {
  initial_offer: 'Opening offer', counter_offer: 'Counter', accept: '✅ Accepted',
  reject: '❌ Rejected', question: 'Question', stall: 'Stalling...',
}

export default function NegotiationThread({ thread }: { thread: NegotiationMessage[] }) {
  return (
    <div className="space-y-2 px-4 py-3">
      {thread.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === 'buyer' ? 'justify-end' : 'justify-start'}`}>
          <div className={`max-w-xs rounded-2xl px-4 py-2.5 text-sm
            ${msg.role === 'buyer'
              ? 'bg-indigo-600 text-white rounded-br-sm'
              : 'bg-slate-100 text-slate-800 rounded-bl-sm'}`}>
            <div>{msg.text}</div>
            <div className={`text-xs mt-1 opacity-70`}>
              {ACT_LABEL[msg.act] ?? msg.act}
              {msg.price != null && ` · €${msg.price}`}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Replace `src/screens/NegotiateScreen.tsx`**

```tsx
import { useState } from 'react'
import { SessionState } from '../api'
import StepBar from '../components/StepBar'
import NegotiationThread from '../components/NegotiationThread'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props { state: SessionState; onFeedback: (choice: string) => Promise<void> }

export default function NegotiateScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const thread = state.negotiation_thread ?? []
  const decision = state.pending_decision!
  const listing = state.ranked_candidates?.[0]

  const handleChoice = async (choice: string) => {
    setLoading(true)
    await onFeedback(choice)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4">
      <div className="w-full max-w-md">
        <div className="text-xl font-black text-indigo-600 py-4">buybot</div>
        <StepBar status="negotiating" />

        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mt-4">
          {listing && (
            <div className="px-4 pt-4 pb-2 border-b border-slate-100">
              <div className="text-xs text-slate-400 uppercase tracking-wide font-semibold">Negotiating</div>
              <div className="font-semibold text-slate-800 text-sm mt-0.5 truncate">{listing.title}</div>
              <div className="text-slate-500 text-xs">Listed at €{listing.price_eur}</div>
            </div>
          )}
          <NegotiationThread thread={thread} />
          <CheckpointBanner decision={decision} onChoice={handleChoice} loading={loading} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: NegotiateScreen (CP2) + NegotiationThread component"
```

---

### Task 17: MeetupScreen (CP3) + DoneScreen

**Files:**
- Modify: `frontend/src/screens/MeetupScreen.tsx`
- Modify: `frontend/src/screens/DoneScreen.tsx`

- [ ] **Step 1: Replace `src/screens/MeetupScreen.tsx`**

```tsx
import { useState } from 'react'
import { SessionState } from '../api'
import StepBar from '../components/StepBar'
import CheckpointBanner from '../components/CheckpointBanner'

interface Props { state: SessionState; onFeedback: (choice: string) => Promise<void> }

export default function MeetupScreen({ state, onFeedback }: Props) {
  const [loading, setLoading] = useState(false)
  const decision = state.pending_decision!
  const proposal = decision.context.meetup_proposal as any

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4">
      <div className="w-full max-w-md">
        <div className="text-xl font-black text-indigo-600 py-4">buybot</div>
        <StepBar status="coordinating" />

        <div className="bg-white rounded-2xl shadow-lg overflow-hidden mt-4">
          <div className="px-4 pt-4 pb-3">
            <div className="text-xs text-slate-400 uppercase tracking-wide font-semibold mb-3">Meetup plan</div>

            <div className="bg-slate-50 rounded-xl p-4 space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-xl">📍</span>
                <div>
                  <div className="font-bold text-slate-800">{proposal?.location}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{proposal?.reason}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xl">🕐</span>
                <div className="font-semibold text-slate-700">{proposal?.time_suggestion}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xl">🚇</span>
                <div className="text-slate-600 text-sm">
                  {proposal?.buyer_route?.duration_text} from you
                </div>
              </div>
              {state.final_price && (
                <div className="flex items-center gap-3">
                  <span className="text-xl">💰</span>
                  <div className="font-bold text-emerald-600 text-lg">
                    Agreed: €{state.final_price}
                  </div>
                </div>
              )}
            </div>
          </div>
          <CheckpointBanner
            decision={decision}
            onChoice={async (c) => { setLoading(true); await onFeedback(c) }}
            loading={loading}
          />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Replace `src/screens/DoneScreen.tsx`**

```tsx
import { SessionState } from '../api'

export default function DoneScreen({ state }: { state: SessionState }) {
  const p = state.meetup_proposal

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
        <div className="text-5xl mb-4">🎉</div>
        <div className="text-xl font-black text-slate-800 mb-1">You're all set!</div>
        <div className="text-slate-500 text-sm mb-6">
          buybot handled the search, negotiation, and scheduling — you just showed up.
        </div>
        <div className="bg-slate-50 rounded-xl p-4 text-left space-y-2 mb-6">
          <div className="flex items-center gap-2 text-sm">
            <span>📍</span>
            <span className="font-semibold text-slate-700">{p?.location}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span>🕐</span>
            <span className="text-slate-600">{p?.time_suggestion}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span>💰</span>
            <span className="font-bold text-emerald-600">€{p?.final_price} agreed</span>
          </div>
        </div>
        <button onClick={() => window.location.href = '/'}
          className="w-full bg-indigo-600 text-white font-bold py-3 rounded-xl text-sm">
          Start a new search
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/screens/MeetupScreen.tsx frontend/src/screens/DoneScreen.tsx
git commit -m "feat: MeetupScreen (CP3) + DoneScreen"
```

---

### Task 18: Admin / Agent view

**Files:**
- Modify: `frontend/src/admin/AgentView.tsx`

- [ ] **Step 1: Replace `src/admin/AgentView.tsx`**

```tsx
import { useState, useEffect } from 'react'
import { useSession, AgentLogEntry } from '../useSession'
import { createSession } from '../api'

const TOOL_BADGE: Record<string, { label: string; color: string }> = {
  search:    { label: 'TAVILY',   color: 'bg-sky-900 text-sky-300' },
  extract:   { label: 'PIONEER',  color: 'bg-purple-900 text-purple-300' },
  analyst:   { label: 'GEMINI',   color: 'bg-emerald-900 text-emerald-300' },
  negotiate: { label: 'GEMINI',   color: 'bg-emerald-900 text-emerald-300' },
  coordinate:{ label: 'GEMINI',   color: 'bg-emerald-900 text-emerald-300' },
  orchestrator: { label: 'SYSTEM', color: 'bg-slate-700 text-slate-400' },
}

export default function AgentView() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const { state, logs } = useSession(sessionId)

  const start = async () => {
    const id = await createSession({
      query: 'iPhone 14', budget: 200,
      condition: 'good+', location: 'München', max_distance_km: 15,
    })
    setSessionId(id)
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-mono p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="text-indigo-400 font-bold text-xl">buybot / agent view</div>
            <div className="text-slate-500 text-xs mt-0.5">internal · for demo purposes</div>
          </div>
          {!sessionId && (
            <button onClick={start}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-bold">
              Run demo
            </button>
          )}
          {state?.status && (
            <span className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-xs">
              status: {state.status}
            </span>
          )}
        </div>

        {state?.degraded && state.degraded.length > 0 && (
          <div className="bg-yellow-900/40 border border-yellow-600 rounded-lg px-4 py-2 mb-4 text-yellow-300 text-xs">
            ⚠ Degraded: {state.degraded.join(' · ')}
          </div>
        )}

        <div className="space-y-2">
          {logs.map((log, i) => {
            const badge = TOOL_BADGE[log.agent] ?? TOOL_BADGE.orchestrator
            return (
              <div key={i} className="flex gap-3 items-start bg-slate-800/50 rounded-lg px-3 py-2">
                <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-bold ${badge.color}`}>
                  {badge.label}
                </span>
                <span className="text-slate-300 text-sm flex-1">{log.msg}</span>
                <span className="text-slate-600 text-xs shrink-0">
                  {new Date(log.ts).toLocaleTimeString()}
                </span>
              </div>
            )
          })}
          {logs.length === 0 && (
            <div className="text-slate-600 text-sm py-8 text-center">
              Click "Run demo" to start the agent pipeline
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/admin/AgentView.tsx
git commit -m "feat: admin AgentView with tool badges and live log feed"
```

---

## Phase 7 — Eval Table & Security

### Task 19: Pioneer eval table

**Files:**
- Create: `eval/gliner_vs_gemini.py`

- [ ] **Step 1: Create `eval/gliner_vs_gemini.py`**

```python
"""
GLiNER2 (via Pioneer) vs Gemini: accuracy / latency / cost comparison.
Run: python eval/gliner_vs_gemini.py
"""
import os, json, time, statistics
from dotenv import load_dotenv; load_dotenv()
import httpx
import google.generativeai as genai

SAMPLES = [
    {
        "text": "iPhone 14 128GB Space Grey. Sehr guter Zustand, keine Kratzer. €175. München Schwabing.",
        "expected": {"brand": "Apple", "model": "iPhone 14 128GB Space Grey",
                     "condition": "very_good", "price_eur": 175.0, "location_city": "München"}
    },
    {
        "text": "Sony A7 III Kamera mit 28-70mm Objektiv. Guter Zustand. €890 VHB. Berlin Mitte.",
        "expected": {"brand": "Sony", "model": "A7 III",
                     "condition": "good", "price_eur": 890.0, "location_city": "Berlin"}
    },
    {
        "text": "MacBook Air M2 256GB Space Gray - wie neu, 6 Monate alt, €950.",
        "expected": {"brand": "Apple", "model": "MacBook Air M2 256GB",
                     "condition": "like_new", "price_eur": 950.0, "location_city": None}
    },
]

LISTING_PROMPT_TEMPLATE = """Extract from this second-hand listing. Return JSON only, no markdown:
{{"brand": str, "model": str, "condition": "new"|"like_new"|"very_good"|"good"|"acceptable",
 "price_eur": float|null, "location_city": str|null, "defects": [str]}}
Listing: {text}"""

def _call_pioneer(text: str) -> tuple[dict, float]:
    endpoint = os.environ["PIONEER_ENDPOINT"]
    prompt = LISTING_PROMPT_TEMPLATE.format(text=text)
    t0 = time.perf_counter()
    resp = httpx.post(endpoint, json={"prompt": prompt}, timeout=10.0)
    elapsed = time.perf_counter() - t0
    return resp.json(), elapsed

def _call_gemini(text: str) -> tuple[dict, float]:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = LISTING_PROMPT_TEMPLATE.format(text=text)
    t0 = time.perf_counter()
    result = model.generate_content(prompt)
    elapsed = time.perf_counter() - t0
    raw = result.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(raw), elapsed

def _score(predicted: dict, expected: dict) -> float:
    fields = ["brand", "model", "condition", "price_eur", "location_city"]
    correct = sum(
        1 for f in fields
        if str(predicted.get(f, "")).lower() == str(expected.get(f, "")).lower()
    )
    return correct / len(fields)

def run():
    pioneer_scores, pioneer_latencies = [], []
    gemini_scores, gemini_latencies = [], []

    for s in SAMPLES:
        try:
            p_out, p_lat = _call_pioneer(s["text"])
            pioneer_scores.append(_score(p_out, s["expected"]))
            pioneer_latencies.append(p_lat)
        except Exception as e:
            print(f"Pioneer error: {e}")
            pioneer_scores.append(0.0)
            pioneer_latencies.append(999.0)

        try:
            g_out, g_lat = _call_gemini(s["text"])
            gemini_scores.append(_score(g_out, s["expected"]))
            gemini_latencies.append(g_lat)
        except Exception as e:
            print(f"Gemini error: {e}")
            gemini_scores.append(0.0)
            gemini_latencies.append(999.0)

    print("\n=== GLiNER2 (Pioneer) vs Gemini Flash — Extraction Benchmark ===\n")
    print(f"{'Metric':<25} {'GLiNER2/Pioneer':>18} {'Gemini Flash':>14}")
    print("-" * 60)
    print(f"{'Accuracy (avg)':<25} {statistics.mean(pioneer_scores)*100:>17.1f}% {statistics.mean(gemini_scores)*100:>13.1f}%")
    print(f"{'Latency p50 (ms)':<25} {statistics.median(pioneer_latencies)*1000:>17.0f}  {statistics.median(gemini_latencies)*1000:>13.0f}")
    print(f"{'Latency p95 (ms)':<25} {max(pioneer_latencies)*1000:>17.0f}  {max(gemini_latencies)*1000:>13.0f}")
    print(f"{'Cost per call (est.)':<25} {'~$0.00003':>18} {'~$0.003':>14}")
    print()

if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Run the eval (once Pioneer endpoint is available)**

```bash
cd eval
python gliner_vs_gemini.py
```
Expected: table with accuracy ≥ 70% for both, GLiNER2 latency < 200ms.

- [ ] **Step 3: Commit**

```bash
git add eval/
git commit -m "feat: Pioneer/GLiNER2 vs Gemini eval script"
```

---

### Task 20: Aikido security setup

- [ ] **Step 1: Connect repo to Aikido**

Go to https://app.aikido.dev → New project → Connect GitHub → select this repo.

- [ ] **Step 2: Add `.aikido.yaml` to configure scope**

Create `.aikido.yaml`:
```yaml
version: 1
exclude:
  - "eval/**"
  - "frontend/node_modules/**"
  - ".superpowers/**"
```

- [ ] **Step 3: Trigger first scan**

Push the `.aikido.yaml` commit — Aikido auto-scans on push.

- [ ] **Step 4: Fix any flagged issues before submission**

Common issues to watch for:
- Any API key accidentally committed → remove from git history with `git filter-repo`
- Vulnerable dependency versions → bump in `pyproject.toml` or `package.json`
- SSRF risk: ensure `TAVILY_API_KEY` is always read from env, never constructed from user input

- [ ] **Step 5: Screenshot clean report**

After all issues are resolved, screenshot the Aikido dashboard showing 0 critical issues.

- [ ] **Step 6: Commit**

```bash
git add .aikido.yaml
git commit -m "chore: add Aikido security scan config"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by |
|---|---|
| 5 agent roles | Tasks 5, 6, 7, 8, 9, 10 |
| 3 human checkpoints with `interrupt()` | Tasks 8, 9 |
| `ProcurementState` incl. `pending_decision`, `decision_history`, `degraded`, `current_candidate_index` | Task 3 |
| `NegotiationMessage` with `act` + `price` | Task 3 |
| Tavily search + mock fallback | Task 5 |
| GLiNER2 extraction + Gemini fallback | Task 6 |
| Analyst scoring algorithm | Task 7 |
| Mock seller for negotiation demo | Task 4 |
| Google Maps route calculation | Task 9 |
| FastAPI 5 endpoints | Task 11 |
| WebSocket (lightweight events) + 2s polling | Tasks 11, 12 |
| React screens: Input, Processing, Choose, Negotiate, Meetup, Done | Tasks 13–17 |
| Admin agent view with tool badges | Task 18 |
| Pioneer eval table | Task 19 |
| Aikido security setup | Task 20 |
| `degraded` visible in admin view | Task 18 |

All spec requirements covered. No gaps found.
