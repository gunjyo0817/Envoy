import uuid, asyncio, os, urllib.parse, threading, secrets
import httpx
from dotenv import load_dotenv
load_dotenv()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "855648623975-dp7249vk7c23jec841cs5favcd7f9tl9.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command

from app.graph import get_graph
from app.state import initial_state
from app.sessions import register_ws, unregister_ws, broadcast, get_logs
from app.auth import (
    init_db, signup, login, user_id_for_token, get_settings, update_settings, AuthError,
    find_or_create_google_user, public_user_for_token, set_onboarded,
)
from app.services import translate, identify_product, reverse_geocode, match_seeded_listing
from app import store, gcal
from app.telegram import notify_seller, notify_seller_time, notify_buyer, poll_updates, mint_link_token

app = FastAPI(title="Envoy API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
init_db()
store.init_store()

_sessions: dict[str, dict] = {}   # session_id → {thread_id, last_state}
_session_locks: dict[str, threading.Lock] = {}
_oauth_states: dict[str, int] = {}   # oauth state -> app user_id


def _lock_for(session_id: str) -> threading.Lock:
    return _session_locks.setdefault(session_id, threading.Lock())


class SessionRequest(BaseModel):
    query: str
    budget_min: float = 0.0
    budget_max: float | None = None
    budget: float | None = None  # legacy alias for budget_max; remove once frontend sends the range
    condition: str = "good+"
    location: str
    max_distance_km: int = 15
    language: str = "en"


class FeedbackRequest(BaseModel):
    choice: str
    free_text: str | None = None


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class SettingsRequest(BaseModel):
    language: str | None = None
    default_address: str | None = None


class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "en"


class CalendarEventRequest(BaseModel):
    summary: str
    location: str = ""
    start_iso: str
    end_iso: str


class VisionRequest(BaseModel):
    image_base64: str


def _on_state_committed(session_id: str, state: dict) -> None:
    """Side effects after a graph step commits: ping the seller / buyer over Telegram, record closed deals."""
    status = state.get("status")
    if status == "awaiting_seller":
        cp = state.get("pending_decision", {}).get("checkpoint")
        if cp == "seller_turn":
            notify_seller(session_id, state["pending_decision"])
        elif cp == "seller_time":
            notify_seller_time(session_id, state["pending_decision"])
    elif status in ("awaiting_human", "coordinating", "done") and state.get("negotiation_thread"):
        last = state["negotiation_thread"][-1]
        thread_len = len(state["negotiation_thread"])
        last_notified_len = _sessions.get(session_id, {}).get("last_notified_len", 0)
        if last["role"] == "seller" and thread_len > last_notified_len:
            verb = {"accept": "accepted your offer", "counter_offer": "sent a counter-offer",
                    "reject": "declined"}.get(last["act"], "replied")
            notify_buyer(
                session_id,
                f"Seller {verb} — review ▸",
                user_id=_sessions.get(session_id, {}).get("user_id"),
            )
            if session_id in _sessions:
                _sessions[session_id]["last_notified_len"] = thread_len

    if status in ("done", "failed"):
        candidates = state.get("ranked_candidates") or []
        idx = state.get("current_candidate_index", 0)
        listing = candidates[idx] if 0 <= idx < len(candidates) else {}
        store.record_deal({
            "session_id": session_id,
            "user_id": _sessions.get(session_id, {}).get("user_id"),
            "query": state.get("query"),
            "thumbnail": listing.get("image_url"),
            "final_price": state.get("final_price"),
            "seller_label": "Kleinanzeigen",
            "meetup": state.get("meetup_proposal"),
            "negotiation_thread": state.get("negotiation_thread") or [],
            "status": status,
        })


def _run_graph(thread_id: str, input_or_command, session_id: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    # Hold a per-session lock across the graph invoke + commit. Both the buyer
    # /feedback handler and the Telegram _resume_seller task can call _run_graph
    # on the same thread_id; concurrent graph.invoke calls would corrupt the
    # MemorySaver checkpoint for that thread.
    with _lock_for(session_id):
        state = dict(graph.invoke(input_or_command, config=config))

        # Dynamic interrupt() stores its payload in the non-serializable
        # __interrupt__ channel, not in state["pending_decision"]. Bridge it so the
        # frontend (which polls pending_decision) sees the checkpoint, and drop the
        # raw Interrupt object so GET /state stays JSON-serializable.
        interrupts = state.pop("__interrupt__", None)
        if interrupts:
            pending = interrupts[0].value
            state["pending_decision"] = pending
            state["status"] = ("awaiting_seller"
                               if isinstance(pending, dict) and pending.get("checkpoint") in ("seller_turn", "seller_time")
                               else "awaiting_human")

        _sessions[session_id]["last_state"] = state
        _on_state_committed(session_id, state)

    agent_name = {
        "searching": "search", "reviewing": "extract",
        "awaiting_human": "analyst", "awaiting_seller": "negotiate",
        "negotiating": "negotiate",
        "coordinating": "coordinate", "done": "coordinate", "failed": "orchestrator",
    }.get(state.get("status", ""), "orchestrator")

    # broadcast is async; schedule it safely from a thread executor context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(broadcast(session_id, {
                    "event": "state_changed",
                    "status": state.get("status"),
                }))
            )
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(broadcast(session_id, {
                    "event": "agent_log",
                    "agent": agent_name,
                    "msg": f"Status: {state.get('status')}. Degraded: {state.get('degraded', [])}",
                }))
            )
    except RuntimeError:
        pass  # No event loop available (e.g. in tests without async context)

    return state


async def _resume_seller(session_id: str, choice: str) -> None:
    if session_id not in _sessions:
        return
    thread_id = _sessions[session_id]["thread_id"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_graph, thread_id, Command(resume=choice), session_id)


@app.on_event("startup")
async def _start_telegram() -> None:
    asyncio.create_task(poll_updates(_resume_seller))


@app.post("/session")
async def create_session(req: SessionRequest, authorization: str | None = Header(default=None)):
    session_id = str(uuid.uuid4())
    thread_id = session_id
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    user_id = user_id_for_token(token)
    _sessions[session_id] = {"thread_id": thread_id, "last_state": None, "user_id": user_id}

    budget_max = req.budget_max if req.budget_max is not None else (req.budget or 200.0)
    state = initial_state(req.query, req.budget_min, budget_max,
                          req.condition, req.location, req.max_distance_km, req.language)
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


class ProposeTimesRequest(BaseModel):
    slots: list[str]


@app.post("/session/{session_id}/propose-times")
async def propose_times(session_id: str, req: ProposeTimesRequest):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    if not req.slots:
        raise HTTPException(status_code=400, detail="At least one slot required")
    thread_id = _sessions[session_id]["thread_id"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, _run_graph, thread_id,
        Command(resume={"action": "reschedule", "slots": req.slots}), session_id)
    return {"ok": True}


@app.get("/session/{session_id}/result")
async def get_result(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    state = _sessions[session_id]["last_state"] or {}
    if state.get("status") != "done":
        raise HTTPException(status_code=400, detail="Session not complete")
    return state.get("meetup_proposal")


def _require_user(authorization: str | None = Header(default=None)) -> int:
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    user_id = user_id_for_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


@app.post("/auth/signup")
async def auth_signup(req: SignupRequest):
    try:
        return signup(req.email, req.password, req.name)
    except AuthError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)


@app.post("/auth/login")
async def auth_login(req: LoginRequest):
    try:
        return login(req.email, req.password)
    except AuthError as e:
        raise HTTPException(status_code=e.code, detail=e.detail)


@app.get("/auth/me")
async def auth_me(user_id: int = Depends(_require_user)):
    from app.auth import _public_user
    return _public_user(user_id)


@app.get("/auth/google/login")
async def google_login():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@app.get("/auth/google/callback")
async def google_callback(code: str | None = None, error: str | None = None):
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/?auth_error=google")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tok = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            tok.raise_for_status()
            access_token = tok.json()["access_token"]
            info = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            info.raise_for_status()
            profile = info.json()
        result = find_or_create_google_user(profile.get("email", ""), profile.get("name", ""))
        return RedirectResponse(f"{FRONTEND_URL}/?token={result['token']}")
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/?auth_error=google")


@app.get("/settings")
async def read_settings(user_id: int = Depends(_require_user)):
    return get_settings(user_id)


@app.put("/settings")
async def write_settings(req: SettingsRequest, user_id: int = Depends(_require_user)):
    return update_settings(user_id, req.language, req.default_address)


@app.post("/onboarding/complete")
async def complete_onboarding(user_id: int = Depends(_require_user)):
    from app.auth import _public_user
    set_onboarded(user_id)
    return _public_user(user_id)


@app.post("/telegram/link-token")
async def telegram_link_token(user_id: int = Depends(_require_user)):
    return mint_link_token(user_id)


@app.get("/telegram/status")
async def telegram_status(user_id: int = Depends(_require_user)):
    return {"connected": store.chat_for_user(user_id) is not None}


@app.get("/deals")
async def read_deals(user_id: int = Depends(_require_user)):
    return store.list_deals(user_id)


@app.get("/deals/{session_id}")
async def read_deal(session_id: str, user_id: int = Depends(_require_user)):
    deal = store.get_deal(session_id)
    if not deal or deal.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@app.get("/calendar/auth-url")
async def calendar_auth_url(user_id: int = Depends(_require_user)):
    state = secrets.token_urlsafe(24)
    _oauth_states[state] = user_id
    return {"url": gcal.auth_url(state)}


@app.get("/calendar/callback")
async def calendar_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    user_id = _oauth_states.pop(state, None) if state else None
    if error or not code or user_id is None:
        return RedirectResponse(f"{FRONTEND_URL}/me?calendar=error")
    try:
        loop = asyncio.get_event_loop()
        tok = await loop.run_in_executor(None, gcal.exchange_code, code)
        store.save_google_tokens(user_id, tok["access_token"], tok["refresh_token"],
                                 tok["expiry"], gcal.SCOPE)
        return RedirectResponse(f"{FRONTEND_URL}/me?calendar=connected")
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/me?calendar=error")


@app.get("/calendar/status")
async def calendar_status(user_id: int = Depends(_require_user)):
    return {"connected": store.get_google_tokens(user_id) is not None}


@app.post("/calendar/event")
async def calendar_event(req: CalendarEventRequest, user_id: int = Depends(_require_user)):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, gcal.insert_event, user_id, req.summary, req.location, req.start_iso, req.end_iso)
    if result is None:
        raise HTTPException(status_code=409, detail="Calendar not connected")
    return result


@app.get("/calendar/freebusy")
async def calendar_freebusy(time_min: str, time_max: str, user_id: int = Depends(_require_user)):
    loop = asyncio.get_event_loop()
    busy = await loop.run_in_executor(None, gcal.query_freebusy, user_id, time_min, time_max)
    return {"busy": busy}


@app.post("/translate")
async def translate_text(req: TranslateRequest):
    loop = asyncio.get_event_loop()
    translation = await loop.run_in_executor(None, translate, req.text, req.target_lang)
    return {"translation": translation}


@app.get("/geocode/reverse")
async def geocode_reverse(lat: float, lng: float):
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=422, detail="Invalid coordinates")
    loop = asyncio.get_event_loop()
    location = await loop.run_in_executor(None, reverse_geocode, lat, lng)
    return {"location": location}


@app.post("/vision/identify")
async def vision_identify(req: VisionRequest):
    loop = asyncio.get_event_loop()
    try:
        query = await loop.run_in_executor(None, identify_product, req.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"query": query}


@app.post("/vision/search")
async def vision_search(req: VisionRequest):
    loop = asyncio.get_event_loop()
    try:
        query = await loop.run_in_executor(None, identify_product, req.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    match = await loop.run_in_executor(None, match_seeded_listing, query)
    return {"query": query, "matched_listing": match}


@app.websocket("/session/{session_id}/stream")
async def websocket_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()

    async def send_fn(event: dict):
        await websocket.send_json(event)

    register_ws(session_id, send_fn)
    for log in get_logs(session_id):
        await websocket.send_json(log)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(session_id, send_fn)
