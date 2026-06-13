# Async Negotiation Core (Plan A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Envoy's synchronous mock-seller flow into a two-sided async system where a real human seller negotiates over Telegram (agent-assisted), the buyer is bridged by Telegram alerts, and completed deals are persisted for history.

**Architecture:** The seller's turn becomes a new LangGraph `interrupt()` (`seller_turn_node`), resumed by a Telegram long-polling handler via `Command(resume=...)`. A `LIVE_SELLER` flag keeps the mock seller in-process for tests/offline (synchronous), and switches to the real Telegram round-trip when on. Graph state stays in `MemorySaver` (the async gap is in-process); `deals` and `telegram_links` are persisted via plain `sqlite3`. Telegram uses raw `httpx` (`getUpdates` long-poll) — no new dependencies.

**Tech Stack:** Python 3 · FastAPI · LangGraph 1.2 (`MemorySaver`, `interrupt`, `Command`) · sqlite3 (stdlib) · httpx · React 19 + Vite + TS.

**Scope deviations from spec (deliberate):**
- `MemorySaver` retained instead of `SqliteSaver` — async gap is in-process; restart-survival dropped (not demo-critical). `deals`/`telegram_links` use plain sqlite.
- Only the **round-1** seller turn is async/real. Round-2's final seller reply (off the demo happy path) stays mock.
- Telegram via raw `httpx` long-polling, not `python-telegram-bot`.

---

## File Structure

- `backend/app/store.py` (**new**) — `deals` + `telegram_links` tables and their CRUD. One responsibility: persistence of deals and Telegram chat links.
- `backend/app/telegram.py` (**new**) — Telegram I/O: send messages/buttons, `notify_seller`, `notify_buyer`, `getUpdates` long-poll loop, update dispatch. One responsibility: Telegram transport.
- `backend/app/state.py` (modify) — add `awaiting_seller` to the `status` Literal.
- `backend/app/agents/negotiate.py` (modify) — split `decide_offer_node` (buyer-only) and add `seller_turn_node` + `LIVE_SELLER` handling + `_gemini_seller_suggestion`.
- `backend/app/graph.py` (modify) — wire `seller_turn` node and its routing.
- `backend/app/mock/listings.py` (modify) — add the seeded demo item (real photo, stable id).
- `backend/app/services.py` (modify) — add `match_seeded_listing(query)` image-search matcher.
- `backend/app/main.py` (modify) — startup poll task; `awaiting_seller` → `notify_seller`; seller-reply resume; `POST /vision/search`; `GET /deals`, `GET /deals/{id}`; write a `deals` row on `done`/`failed`.
- `backend/tests/test_store.py`, `test_seller_turn.py`, `test_telegram.py`, `test_vision_search.py`, `test_deals_api.py` (**new**).
- `frontend/src/screens/InputScreen.tsx` (modify) — photo-search upload.
- `frontend/src/screens/ProcessingScreen.tsx` (modify) — `awaiting_seller` "Waiting for seller…" state.
- `frontend/src/App.tsx` (modify) — route `awaiting_seller` to ProcessingScreen.

---

## Task 1: `store.py` — deals + telegram_links persistence

**Files:**
- Create: `backend/app/store.py`
- Test: `backend/tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_store.py
import os, tempfile, importlib


def _fresh_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["ENVOY_DB"] = path
    import app.store as store
    importlib.reload(store)
    store.init_store()
    return store, path


def test_telegram_link_roundtrip():
    store, _ = _fresh_store()
    store.register_chat(chat_id=111, role="seller")
    store.attach_session(chat_id=111, session_id="s-1")
    link = store.resolve_chat(111)
    assert link["role"] == "seller" and link["session_id"] == "s-1"
    assert store.chat_for_role("seller") == 111


def test_record_and_list_deals():
    store, _ = _fresh_store()
    store.record_deal({
        "session_id": "s-2", "user_id": 7, "query": "iPhone 14",
        "thumbnail": "http://img", "final_price": 180.0,
        "seller_label": "Kleinanzeigen", "meetup": {"location": "Marienplatz"},
        "status": "done",
    })
    deals = store.list_deals(user_id=7)
    assert len(deals) == 1 and deals[0]["final_price"] == 180.0
    assert deals[0]["meetup"]["location"] == "Marienplatz"
    assert store.get_deal("s-2")["status"] == "done"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.store'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/store.py
"""Persistence for completed deals and Telegram chat links (stdlib sqlite3)."""
import os, json, sqlite3, datetime

_DB_PATH = os.environ.get("ENVOY_DB", os.path.join(os.path.dirname(__file__), "..", "envoy.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(os.environ.get("ENVOY_DB", _DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_store() -> None:
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS telegram_links (
                chat_id    INTEGER PRIMARY KEY,
                role       TEXT NOT NULL,
                user_id    INTEGER,
                session_id TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS deals (
                session_id   TEXT PRIMARY KEY,
                user_id      INTEGER,
                query        TEXT,
                thumbnail    TEXT,
                final_price  REAL,
                seller_label TEXT,
                meetup       TEXT,
                status       TEXT,
                created_at   TEXT,
                closed_at    TEXT
            )"""
        )


def register_chat(chat_id: int, role: str, user_id: int | None = None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO telegram_links (chat_id, role, user_id) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET role=excluded.role, user_id=excluded.user_id",
            (chat_id, role, user_id),
        )


def attach_session(chat_id: int, session_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE telegram_links SET session_id=? WHERE chat_id=?", (session_id, chat_id))


def resolve_chat(chat_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM telegram_links WHERE chat_id=?", (chat_id,)).fetchone()
    return dict(row) if row else None


def chat_for_role(role: str) -> int | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT chat_id FROM telegram_links WHERE role=? ORDER BY rowid DESC LIMIT 1", (role,)
        ).fetchone()
    return row["chat_id"] if row else None


def record_deal(deal: dict) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO deals
               (session_id, user_id, query, thumbnail, final_price, seller_label, meetup, status, created_at, closed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 final_price=excluded.final_price, meetup=excluded.meetup,
                 status=excluded.status, closed_at=excluded.closed_at""",
            (deal["session_id"], deal.get("user_id"), deal.get("query"), deal.get("thumbnail"),
             deal.get("final_price"), deal.get("seller_label"),
             json.dumps(deal.get("meetup") or {}), deal.get("status"), now, now),
        )


def _row_to_deal(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["meetup"] = json.loads(d.get("meetup") or "{}")
    return d


def list_deals(user_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM deals WHERE user_id=? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
    return [_row_to_deal(r) for r in rows]


def get_deal(session_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM deals WHERE session_id=?", (session_id,)).fetchone()
    return _row_to_deal(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_store.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/store.py backend/tests/test_store.py
git commit -m "feat: deals + telegram_links persistence store"
```

---

## Task 2: Add `awaiting_seller` status

**Files:**
- Modify: `backend/app/state.py:46-49`

- [ ] **Step 1: Add the status literal**

In `backend/app/state.py`, change the `status` field of `ProcurementState`:

```python
    status: Literal[
        "searching", "reviewing", "awaiting_human", "awaiting_seller",
        "negotiating", "coordinating", "done", "failed"
    ]
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd backend && python -m pytest tests/test_state.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/state.py
git commit -m "feat: add awaiting_seller status"
```

---

## Task 3: Split `decide_offer_node` and add `seller_turn_node`

The buyer decision and the seller turn become two nodes. `LIVE_SELLER=false` (default) keeps the seller turn synchronous on the mock, preserving current end-to-end behavior; `LIVE_SELLER=true` makes it an `interrupt()` resumed by Telegram.

**Files:**
- Modify: `backend/app/agents/negotiate.py`
- Test: `backend/tests/test_seller_turn.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_seller_turn.py
import os
from unittest.mock import patch
from app.agents.negotiate import decide_offer_node, seller_turn_node


def _state(buyer_price=170.0, listing=200.0):
    return {
        "current_candidate_index": 0,
        "ranked_candidates": [{"price_eur": listing, "title": "iPhone 14"}],
        "budget_max": 250.0,
        "language": "en",
        "negotiation_thread": [
            {"role": "buyer", "text": "offer", "act": "initial_offer", "price": buyer_price, "ts": "t"},
        ],
        "decision_history": [],
        "degraded": [],
        "pending_decision": {
            "checkpoint": "confirm_offer",
            "summary": "", "options": [],
            "context": {"offer_price": buyer_price, "listing_price": listing},
        },
    }


def test_decide_offer_approve_routes_to_seller_and_sets_awaiting():
    with patch("app.agents.negotiate.interrupt", return_value="approve"), \
         patch("app.agents.negotiate._gemini_seller_suggestion",
               return_value={"counter_price": 185.0, "message_text": "How about 185?"}):
        out = decide_offer_node(_state())
    assert out["status"] == "awaiting_seller"
    assert out["pending_decision"]["checkpoint"] == "seller_turn"
    assert out["pending_decision"]["context"]["buyer_offer"] == 170.0
    assert out["pending_decision"]["context"]["suggested_counter"] == 185.0


def test_decide_offer_skip_advances_candidate():
    with patch("app.agents.negotiate.interrupt", return_value="skip"):
        out = decide_offer_node(_state())
    assert out["current_candidate_index"] == 1
    assert out["status"] == "negotiating"


def test_seller_turn_mock_accept_when_offer_high(monkeypatch):
    monkeypatch.delenv("LIVE_SELLER", raising=False)  # mock path
    st = _state(buyer_price=195.0, listing=200.0)  # >= 95% → accept
    st["pending_decision"] = {
        "checkpoint": "seller_turn", "summary": "", "options": [],
        "context": {"buyer_offer": 195.0, "listing_price": 200.0, "suggested_counter": 190.0},
    }
    out = seller_turn_node(st)
    assert out["status"] == "coordinating"
    assert out["final_price"] == 195.0
    assert out["negotiation_thread"][-1]["role"] == "seller"
    assert out["negotiation_thread"][-1]["act"] == "accept"


def test_seller_turn_live_counter(monkeypatch):
    monkeypatch.setenv("LIVE_SELLER", "true")
    st = _state(buyer_price=170.0, listing=200.0)
    st["pending_decision"] = {
        "checkpoint": "seller_turn", "summary": "", "options": [],
        "context": {"buyer_offer": 170.0, "listing_price": 200.0, "suggested_counter": 185.0,
                    "draft_text": "How about 185?"},
    }
    with patch("app.agents.negotiate.interrupt", return_value="counter"):
        out = seller_turn_node(st)
    assert out["status"] == "negotiating"
    last = out["negotiation_thread"][-1]
    assert last["role"] == "seller" and last["act"] == "counter_offer" and last["price"] == 185.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_seller_turn.py -v`
Expected: FAIL — `ImportError: cannot import name 'seller_turn_node'`

- [ ] **Step 3: Implement the split**

In `backend/app/agents/negotiate.py`, add the `os` flag helper and the seller suggestion near the top (after the existing imports — `os` is already imported):

```python
def _live_seller() -> bool:
    return os.environ.get("LIVE_SELLER", "false").lower() == "true"


def _gemini_seller_suggestion(listing_price: float, buyer_offer: float, language: str = "en") -> dict:
    """Agent-drafted seller reply: a counter price + short message. Deterministic fallback on error."""
    suggested = round((buyer_offer + listing_price) / 2)
    suggested = max(int(buyer_offer) + 1, min(suggested, int(listing_price)))
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-3.5-flash")
        prompt = (
            f"You advise a SELLER. Listing price €{listing_price:.0f}; buyer offered €{buyer_offer:.0f}. "
            f"Suggest a counter at €{suggested} and a short polite message in {_lang_name(language)}. "
            f"Return JSON only: {{\"counter_price\": float, \"message_text\": str}}"
        )
        text = model.generate_content(prompt).text.strip()
        text = text.removeprefix("```json").removesuffix("```").strip()
        data = json.loads(text)
        data.setdefault("counter_price", float(suggested))
        data.setdefault("message_text", f"Wie wäre es mit €{suggested}?")
        return data
    except Exception:
        return {"counter_price": float(suggested), "message_text": f"Wie wäre es mit €{suggested}?"}
```

Now replace the **entire `decide_offer_node`** (lines 101-154) with the buyer-only version plus the new `seller_turn_node`:

```python
def decide_offer_node(state: ProcurementState) -> dict:
    """Buyer decision on the opening offer. On approve/lower, hand to the seller turn."""
    degraded = list(state.get("degraded", []))
    idx = state["current_candidate_index"]
    listing_price = _listing_price(state)
    thread = list(state["negotiation_thread"])
    language = state.get("language", "en")

    choice = interrupt(state["pending_decision"])
    entry = {"checkpoint": "confirm_offer", "choice": choice, "ts": _ts()}
    history = state["decision_history"] + [entry]

    if choice == "skip":
        return {
            "negotiation_thread": [], "current_candidate_index": idx + 1,
            "decision_history": history, "status": "negotiating",
            "pending_decision": None, "degraded": list(set(degraded)),
        }

    offer_price = thread[-1]["price"]
    if choice == "lower":
        offer_price = round(listing_price * 0.78)
        lower_text = (f"Würden Sie €{offer_price:.0f} akzeptieren?" if language == "de"
                      else f"Would you accept €{offer_price:.0f}?")
        thread[-1] = {**thread[-1], "price": float(offer_price), "text": lower_text}

    suggestion = _gemini_seller_suggestion(listing_price, offer_price, language)
    listing = state["ranked_candidates"][idx]
    seller_pending: PendingDecision = {
        "checkpoint": "seller_turn",
        "summary": f"Buyer offers €{offer_price:.0f} for {listing.get('title', 'item')} "
                   f"(listed €{listing_price:.0f}). Reply?",
        "options": [
            {"id": "accept", "label": f"Accept €{offer_price:.0f}"},
            {"id": "counter", "label": f"Counter €{suggestion['counter_price']:.0f}"},
            {"id": "reject", "label": "Reject"},
        ],
        "context": {
            "buyer_offer": float(offer_price), "listing_price": float(listing_price),
            "suggested_counter": float(suggestion["counter_price"]),
            "draft_text": suggestion["message_text"],
        },
    }
    return {
        "negotiation_thread": thread, "decision_history": history,
        "pending_decision": seller_pending, "status": "awaiting_seller",
        "degraded": list(set(degraded)),
    }


def _apply_seller_choice(state: ProcurementState, choice: str) -> dict:
    """Turn a seller choice ('accept'|'reject'|'counter'|'counter:<price>') into state updates."""
    degraded = list(state.get("degraded", []))
    idx = state["current_candidate_index"]
    thread = list(state["negotiation_thread"])
    ctx = state["pending_decision"]["context"]
    buyer_offer = ctx["buyer_offer"]
    base = {"decision_history": state["decision_history"],
            "degraded": list(set(degraded)), "pending_decision": None}

    if choice == "accept":
        thread.append({"role": "seller", "text": f"OK, €{buyer_offer:.0f} passt.",
                       "act": "accept", "price": float(buyer_offer), "ts": _ts()})
        return {**base, "negotiation_thread": thread,
                "final_price": float(buyer_offer), "status": "coordinating"}
    if choice == "reject":
        thread.append({"role": "seller", "text": "Tut mir leid, Preis ist fest.",
                       "act": "reject", "price": None, "ts": _ts()})
        return {**base, "negotiation_thread": [], "current_candidate_index": idx + 1,
                "status": "negotiating"}
    # counter (optionally "counter:<price>")
    price = ctx["suggested_counter"]
    if isinstance(choice, str) and choice.startswith("counter:"):
        try:
            price = float(choice.split(":", 1)[1])
        except ValueError:
            pass
    thread.append({"role": "seller", "text": ctx.get("draft_text", f"Wie wäre es mit €{price:.0f}?"),
                   "act": "counter_offer", "price": float(price), "ts": _ts()})
    return {**base, "negotiation_thread": thread, "status": "negotiating"}


def seller_turn_node(state: ProcurementState) -> dict:
    """The seller's response. Async via Telegram interrupt when LIVE_SELLER, else the mock."""
    if _live_seller():
        choice = interrupt(state["pending_decision"])
    else:
        ctx = state["pending_decision"]["context"]
        reply = mock_seller_response(ctx["listing_price"], ctx["buyer_offer"])
        choice = {"accept": "accept", "reject": "reject",
                  "counter_offer": "counter"}.get(reply["act"], "counter")
    return _apply_seller_choice(state, choice)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_seller_turn.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/negotiate.py backend/tests/test_seller_turn.py
git commit -m "feat: split buyer decision and async seller turn"
```

---

## Task 4: Wire `seller_turn` into the graph

**Files:**
- Modify: `backend/app/graph.py`
- Test: `backend/tests/test_graph_seller.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_graph_seller.py
import os
from unittest.mock import patch
from langgraph.graph import END
from app.graph import _after_decide_offer, _after_seller_turn


def test_after_decide_offer_routes_to_seller_turn():
    assert _after_decide_offer({"status": "awaiting_seller", "negotiation_thread": []}) == "seller_turn"


def test_after_decide_offer_skip_retries_candidate():
    # skip set status negotiating with an empty thread → next candidate
    assert _after_decide_offer({"status": "negotiating", "negotiation_thread": []}) == "make_offer"


def test_after_seller_turn_accept_to_meetup():
    assert _after_seller_turn({"status": "coordinating", "negotiation_thread": []}) == "plan_meetup"


def test_after_seller_turn_counter_to_round2():
    state = {"status": "negotiating",
             "negotiation_thread": [{"role": "seller", "act": "counter_offer", "price": 185.0}]}
    assert _after_seller_turn(state) == "make_counter"


def test_after_seller_turn_reject_next_candidate():
    assert _after_seller_turn({"status": "negotiating", "negotiation_thread": []}) == "make_offer"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_graph_seller.py -v`
Expected: FAIL — `ImportError: cannot import name '_after_seller_turn'`

- [ ] **Step 3: Update the graph**

In `backend/app/graph.py`, update the import and routing. Replace the `_after_decide_offer` function and add `_after_seller_turn`:

```python
from app.agents.negotiate import (
    make_offer_node, decide_offer_node, seller_turn_node,
    make_counter_node, decide_counter_node,
)
```

```python
def _after_decide_offer(state: ProcurementState) -> str:
    if state["status"] == "awaiting_seller":
        return "seller_turn"
    if state["status"] == "failed":
        return END
    return "make_offer"  # skip → next candidate


def _after_seller_turn(state: ProcurementState) -> str:
    if state["status"] == "coordinating":
        return "plan_meetup"
    if state["status"] == "failed":
        return END
    thread = state.get("negotiation_thread") or []
    if thread and thread[-1]["role"] == "seller":
        return "make_counter"   # seller countered → round 2
    return "make_offer"         # rejected → next candidate
```

In `build_graph()`, register the node and edges. Add after the `decide_offer` node registration:

```python
    builder.add_node("seller_turn", seller_turn_node)
```

Replace the `decide_offer` conditional edges block with:

```python
    builder.add_conditional_edges(
        "decide_offer",
        _after_decide_offer,
        {"seller_turn": "seller_turn", "make_offer": "make_offer", END: END},
    )
    builder.add_conditional_edges(
        "seller_turn",
        _after_seller_turn,
        {"make_offer": "make_offer", "make_counter": "make_counter",
         "plan_meetup": "plan_meetup", END: END},
    )
```

- [ ] **Step 4: Run the new test and the full backend suite**

Run: `cd backend && python -m pytest tests/test_graph_seller.py tests/test_api.py -v`
Expected: PASS — the new routing tests pass, and `test_api.py` still completes synchronously (LIVE_SELLER unset → mock seller path).

- [ ] **Step 5: Commit**

```bash
git add backend/app/graph.py backend/tests/test_graph_seller.py
git commit -m "feat: wire async seller_turn node into the graph"
```

---

## Task 5: Telegram transport (`telegram.py`)

**Files:**
- Create: `backend/app/telegram.py`
- Test: `backend/tests/test_telegram.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_telegram.py
from unittest.mock import patch, MagicMock
import app.telegram as tg


def test_send_message_posts_to_telegram():
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "T"}), \
         patch("app.telegram.httpx.post") as post:
        post.return_value = MagicMock(status_code=200)
        tg.tg_send(chat_id=42, text="hello", buttons=[("Accept €5", "seller:accept")])
    url, kwargs = post.call_args[0][0], post.call_args[1]
    assert url.endswith("/sendMessage")
    assert kwargs["json"]["chat_id"] == 42
    assert kwargs["json"]["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "seller:accept"


def test_build_seller_message_lists_options():
    pending = {
        "summary": "Buyer offers €170 for iPhone 14. Reply?",
        "context": {"buyer_offer": 170.0, "suggested_counter": 185.0, "draft_text": "How about 185?"},
    }
    text, buttons = tg.build_seller_message(pending)
    assert "€170" in text
    cbs = [cb for _, cb in buttons]
    assert "seller:accept" in cbs and "seller:counter" in cbs and "seller:reject" in cbs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_telegram.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.telegram'`

- [ ] **Step 3: Implement the transport**

```python
# backend/app/telegram.py
"""Telegram transport via raw httpx getUpdates long-polling. No external bot lib."""
import os, asyncio
import httpx
from app import store

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


def _api(method: str) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return f"https://api.telegram.org/bot{token}/{method}"


def tg_send(chat_id: int, text: str, buttons: list[tuple[str, str]] | None = None) -> None:
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return
    payload: dict = {"chat_id": chat_id, "text": text}
    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": label, "callback_data": data}] for label, data in buttons]
        }
    try:
        httpx.post(_api("sendMessage"), json=payload, timeout=10.0)
    except Exception:
        pass


def build_seller_message(pending: dict) -> tuple[str, list[tuple[str, str]]]:
    ctx = pending["context"]
    offer = ctx["buyer_offer"]
    counter = ctx["suggested_counter"]
    text = (f"{pending['summary']}\n\n"
            f"Agent suggests countering at €{counter:.0f}:\n“{ctx.get('draft_text', '')}”")
    buttons = [
        (f"✅ Accept €{offer:.0f}", "seller:accept"),
        (f"↩️ Counter €{counter:.0f}", "seller:counter"),
        ("❌ Reject", "seller:reject"),
    ]
    return text, buttons


def notify_seller(session_id: str, pending: dict) -> None:
    chat_id = store.chat_for_role("seller")
    if chat_id is None:
        return
    store.attach_session(chat_id, session_id)
    text, buttons = build_seller_message(pending)
    tg_send(chat_id, text, buttons)


def notify_buyer(session_id: str, message: str) -> None:
    chat_id = store.chat_for_role("buyer")
    if chat_id is None:
        return
    tg_send(chat_id, f"{message}\n\n{FRONTEND_URL}/?session={session_id}")


async def poll_updates(on_seller_reply) -> None:
    """Long-poll getUpdates; dispatch /start registration and seller callback taps.

    on_seller_reply(session_id, choice) resumes the graph (injected from main to avoid a cycle).
    """
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return
    offset = 0
    async with httpx.AsyncClient(timeout=35.0) as client:
        while True:
            try:
                resp = await client.get(_api("getUpdates"),
                                        params={"offset": offset, "timeout": 30})
                for upd in resp.json().get("result", []):
                    offset = upd["update_id"] + 1
                    await _dispatch(upd, on_seller_reply)
            except Exception:
                await asyncio.sleep(2.0)


async def _dispatch(upd: dict, on_seller_reply) -> None:
    # /start <role> registration
    msg = upd.get("message")
    if msg and msg.get("text", "").startswith("/start"):
        chat_id = msg["chat"]["id"]
        parts = msg["text"].split()
        role = parts[1] if len(parts) > 1 else "buyer"
        store.register_chat(chat_id, role)
        tg_send(chat_id, f"Registered as {role}. You'll get negotiation updates here.")
        return
    # inline button tap: "seller:accept" | "seller:counter" | "seller:reject"
    cb = upd.get("callback_query")
    if cb and cb.get("data", "").startswith("seller:"):
        chat_id = cb["message"]["chat"]["id"]
        link = store.resolve_chat(chat_id)
        if not link or not link.get("session_id"):
            return
        choice = cb["data"].split(":", 1)[1]
        await on_seller_reply(link["session_id"], choice)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_telegram.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/telegram.py backend/tests/test_telegram.py
git commit -m "feat: telegram transport (long-poll, seller buttons, buyer alerts)"
```

---

## Task 6: Wire Telegram into `main.py` (notify on `awaiting_seller`, resume on reply)

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_seller_resume.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_seller_resume.py
import os, importlib
from unittest.mock import patch


def test_awaiting_seller_triggers_notify(monkeypatch):
    monkeypatch.setenv("LIVE_SELLER", "true")
    import app.main as main
    importlib.reload(main)
    captured = {}

    def fake_notify(session_id, pending):
        captured["session_id"] = session_id
        captured["checkpoint"] = pending["checkpoint"]

    with patch("app.main.notify_seller", fake_notify):
        # Drive a fake state that already reached awaiting_seller via the bridge
        main._sessions["sess"] = {"thread_id": "sess", "last_state": None}
        state = {"status": "awaiting_seller",
                 "pending_decision": {"checkpoint": "seller_turn",
                                      "context": {"buyer_offer": 1, "suggested_counter": 1}}}
        main._on_state_committed("sess", state)
    assert captured["session_id"] == "sess"
    assert captured["checkpoint"] == "seller_turn"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_seller_resume.py -v`
Expected: FAIL — `AttributeError: module 'app.main' has no attribute '_on_state_committed'`

- [ ] **Step 3: Implement the wiring**

In `backend/app/main.py`, add imports near the existing ones:

```python
from app import store
from app.telegram import notify_seller, notify_buyer, poll_updates
```

After `init_db()` add:

```python
store.init_store()
```

Add a small post-commit hook and call it from `_run_graph`. Insert this function above `_run_graph`:

```python
def _on_state_committed(session_id: str, state: dict) -> None:
    """Side effects after a graph step commits: ping the seller / buyer over Telegram."""
    status = state.get("status")
    if status == "awaiting_seller" and state.get("pending_decision", {}).get("checkpoint") == "seller_turn":
        notify_seller(session_id, state["pending_decision"])
    elif status in ("awaiting_human", "coordinating", "done") and state.get("negotiation_thread"):
        last = state["negotiation_thread"][-1]
        if last["role"] == "seller":
            verb = {"accept": "accepted your offer", "counter_offer": "sent a counter-offer",
                    "reject": "declined"}.get(last["act"], "replied")
            notify_buyer(session_id, f"Seller {verb} — review ▸")
```

In `_run_graph`, after the line `_sessions[session_id]["last_state"] = state`, add:

```python
    _on_state_committed(session_id, state)
```

Add the seller-reply resume coroutine and the startup task. After the `_run_graph` definition add:

```python
async def _resume_seller(session_id: str, choice: str) -> None:
    if session_id not in _sessions:
        return
    thread_id = _sessions[session_id]["thread_id"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_graph, thread_id, Command(resume=choice), session_id)


@app.on_event("startup")
async def _start_telegram() -> None:
    asyncio.create_task(poll_updates(_resume_seller))
```

Also, write a `deals` row when a session closes. In `_on_state_committed`, append:

```python
    if status in ("done", "failed"):
        listing = (state.get("ranked_candidates") or [{}])[state.get("current_candidate_index", 0)] \
                  if state.get("ranked_candidates") else {}
        store.record_deal({
            "session_id": session_id,
            "user_id": _sessions.get(session_id, {}).get("user_id"),
            "query": state.get("query"),
            "thumbnail": listing.get("image_url"),
            "final_price": state.get("final_price"),
            "seller_label": "Kleinanzeigen",
            "meetup": state.get("meetup_proposal"),
            "status": status,
        })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_seller_resume.py -v`
Expected: PASS

- [ ] **Step 5: Run the full backend suite (no regressions)**

Run: `cd backend && python -m pytest -q`
Expected: PASS (all tests; LIVE_SELLER unset keeps the synchronous path)

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_seller_resume.py
git commit -m "feat: notify seller on awaiting_seller, resume on telegram reply, record deals"
```

---

## Task 7: Image search → seeded Kleinanzeigen match

**Files:**
- Modify: `backend/app/mock/listings.py`
- Modify: `backend/app/services.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_vision_search.py`

- [ ] **Step 1: Add the seeded demo listing**

In `backend/app/mock/listings.py`, add a `SEEDED_DEMO_LISTING` constant after `FACEBOOK_LISTINGS` (replace the placeholder image URL with the seller's real photo URL during demo prep):

```python
# The seller's real item, presented as a Kleinanzeigen listing. Image search matches this.
SEEDED_DEMO_LISTING = {
    "platform": "kleinanzeigen",
    "listing_id": "demo-seed-001",
    "title": "iPhone 14 128GB Midnight — wie neu",
    "price_text": "€185",
    "location": "Schwabing, München",
    "url": "https://www.kleinanzeigen.de/s-anzeige/demo-seed-001",
    "image_url": "https://example.com/REPLACE_WITH_REAL_PHOTO.jpg",
    "seller_rating": 4.9,
    "seller_reviews": 24,
    "raw_description": "iPhone 14 128GB Midnight. Wie neu, kaum benutzt. Mit Originalverpackung.",
    "match_keywords": ["iphone", "14", "128", "midnight"],
}
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_vision_search.py
from unittest.mock import patch
from app.services import match_seeded_listing


def test_matches_seed_on_keywords():
    listing = match_seeded_listing("iPhone 14 128GB Midnight")
    assert listing is not None
    assert listing["listing_id"] == "demo-seed-001"


def test_no_match_returns_none():
    assert match_seeded_listing("Sony A7 III camera") is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_vision_search.py -v`
Expected: FAIL — `ImportError: cannot import name 'match_seeded_listing'`

- [ ] **Step 4: Implement the matcher**

In `backend/app/services.py`, add at the bottom (and add the import at the top: `from app.mock.listings import SEEDED_DEMO_LISTING`):

```python
def match_seeded_listing(query: str) -> dict | None:
    """Match a product query against the seeded demo listing by keyword overlap."""
    q = (query or "").lower()
    kws = SEEDED_DEMO_LISTING["match_keywords"]
    hits = sum(1 for kw in kws if kw in q)
    return SEEDED_DEMO_LISTING if hits >= max(2, len(kws) - 1) else None
```

- [ ] **Step 5: Add the `/vision/search` endpoint**

In `backend/app/main.py`, add the import `from app.services import translate, identify_product, reverse_geocode, match_seeded_listing` (extend the existing import line) and add the endpoint after `vision_identify`:

```python
@app.post("/vision/search")
async def vision_search(req: VisionRequest):
    loop = asyncio.get_event_loop()
    try:
        query = await loop.run_in_executor(None, identify_product, req.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    match = await loop.run_in_executor(None, match_seeded_listing, query)
    return {"query": query, "matched_listing": match}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_vision_search.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/mock/listings.py backend/app/services.py backend/app/main.py backend/tests/test_vision_search.py
git commit -m "feat: image search matches seeded Kleinanzeigen listing"
```

---

## Task 8: Deals API endpoints

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_deals_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_deals_api.py
from fastapi.testclient import TestClient
from unittest.mock import patch
import app.main as main


def test_list_deals_requires_auth_and_returns_rows():
    client = TestClient(main.app)
    with patch("app.main._require_user", return_value=7), \
         patch("app.main.store.list_deals", return_value=[{"session_id": "s-1", "final_price": 180.0}]):
        main.app.dependency_overrides[main._require_user] = lambda: 7
        resp = client.get("/deals")
        main.app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()[0]["session_id"] == "s-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_deals_api.py -v`
Expected: FAIL — 404 (route not defined)

- [ ] **Step 3: Add the endpoints**

In `backend/app/main.py`, after the settings endpoints add:

```python
@app.get("/deals")
async def read_deals(user_id: int = Depends(_require_user)):
    return store.list_deals(user_id)


@app.get("/deals/{session_id}")
async def read_deal(session_id: str, user_id: int = Depends(_require_user)):
    deal = store.get_deal(session_id)
    if not deal or deal.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_deals_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_deals_api.py
git commit -m "feat: deals list + detail API"
```

---

## Task 9: Frontend — `awaiting_seller` waiting state

**Files:**
- Modify: `frontend/src/App.tsx:24-37`
- Modify: `frontend/src/screens/ProcessingScreen.tsx`

- [ ] **Step 1: Route `awaiting_seller` to ProcessingScreen**

In `frontend/src/App.tsx`, add a branch before the final fallback (after the `negotiating`/`coordinating` block):

```tsx
  if (status === 'awaiting_seller') {
    return <ProcessingScreen status={status} />
  }
```

- [ ] **Step 2: Add a distinct "Waiting for seller" copy in ProcessingScreen**

Open `frontend/src/screens/ProcessingScreen.tsx`. It takes a `status` prop. Add a label map so `awaiting_seller` reads as a calm wait (match the existing component's styling/structure — read the file first and follow its current pattern). Add to the status→label lookup:

```tsx
  const label = status === 'awaiting_seller'
    ? 'Waiting for the seller to respond…'
    : status === 'searching' ? 'Searching listings…'
    : status === 'reviewing' ? 'Reviewing candidates…'
    : status === 'negotiating' ? 'Negotiating…'
    : status === 'coordinating' ? 'Planning the meetup…'
    : 'Working…'
```

(Adapt the exact JSX to the file's existing markup; the requirement is that `awaiting_seller` shows the "Waiting for the seller…" copy and an amber-free, calm spinner consistent with the design system.)

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds with no type errors.

- [ ] **Step 4: Manual check**

Run the app (`cd frontend && npm run dev`), drive a session to the seller wait (with `LIVE_SELLER=true` on the backend), and confirm the screen shows "Waiting for the seller to respond…" and updates over the existing WebSocket when the seller replies.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/screens/ProcessingScreen.tsx
git commit -m "feat: buyer waiting-for-seller state"
```

---

## Task 10: Frontend — photo search on the input screen

**Files:**
- Modify: `frontend/src/screens/InputScreen.tsx`
- Reference: `frontend/src/api.ts` (add a `visionSearch` call)

- [ ] **Step 1: Add the API helper**

Read `frontend/src/api.ts` and follow its existing fetch pattern. Add:

```ts
export async function visionSearch(imageBase64: string): Promise<{ query: string; matched_listing: any | null }> {
  const res = await fetch(`${API_BASE}/vision/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: imageBase64 }),
  })
  if (!res.ok) throw new Error('vision search failed')
  return res.json()
}
```

(Use whatever `API_BASE`/headers convention `api.ts` already defines.)

- [ ] **Step 2: Add a photo upload to InputScreen**

Read `frontend/src/screens/InputScreen.tsx` and follow its existing form/state pattern. Add a file input that reads the file as a base64 data URL, calls `visionSearch`, and on a match pre-fills the query field with `query` (and optionally shows the matched listing's title/thumbnail as a confirmation chip). Keep the manual text entry as the fallback path.

```tsx
const onPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0]
  if (!file) return
  const dataUrl = await new Promise<string>((resolve) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result as string)
    r.readAsDataURL(file)
  })
  const { query, matched_listing } = await visionSearch(dataUrl)
  setQuery(query)               // pre-fill the existing query state
  setMatched(matched_listing)   // optional: show a "Matched: …" chip
}
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Manual check**

Upload the seller's item photo; confirm the query field pre-fills (e.g. "iPhone 14 128GB") and, if wired, the matched-listing chip appears.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/screens/InputScreen.tsx frontend/src/api.ts
git commit -m "feat: photo search prefills query from seeded match"
```

---

## Final verification

- [ ] **Backend suite green:** `cd backend && python -m pytest -q` → all pass.
- [ ] **Frontend build green:** `cd frontend && npm run build` → succeeds.
- [ ] **End-to-end mock (LIVE_SELLER unset):** create a session via the UI; negotiation completes synchronously as before; a `deals` row is written on done.
- [ ] **End-to-end live (LIVE_SELLER=true, TELEGRAM_BOT_TOKEN set):** seller `/start seller` in the bot; buyer `/start buyer`; run a session → buyer approves offer → seller gets buttons on Telegram → taps Counter → buyer's web app updates over WebSocket and the buyer gets a Telegram alert → buyer accepts → meetup → Done → deal appears in `GET /deals`.

---

## Spec coverage check

- Build item 1 (persistence) → Tasks 1, 6 (deals/links via sqlite; MemorySaver retained by design).
- Build item 2 (Telegram channel) → Tasks 5, 6.
- Build item 3 (async seller negotiation) → Tasks 2, 3, 4, 6.
- Build item 4 (image search → seeded match) → Task 7.
- Build item 5 (buyer Telegram alerts + deep links) → Tasks 5 (`notify_buyer`), 6.
- Deals API + buyer waiting UI + photo search → Tasks 8, 9, 10 (history *view* screen is Plan B; the API lands here).
