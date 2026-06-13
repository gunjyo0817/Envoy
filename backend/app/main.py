import uuid, asyncio, os, urllib.parse
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
    find_or_create_google_user, public_user_for_token,
)
from app.services import translate, identify_product, reverse_geocode, match_seeded_listing
from app import store
from app.telegram import notify_seller, notify_buyer, poll_updates

app = FastAPI(title="Envoy API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
init_db()
store.init_store()

_sessions: dict[str, dict] = {}   # session_id → {thread_id, last_state}


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


class VisionRequest(BaseModel):
    image_base64: str


def _on_state_committed(session_id: str, state: dict) -> None:
    """Side effects after a graph step commits: ping the seller / buyer over Telegram, record closed deals."""
    status = state.get("status")
    if status == "awaiting_seller" and state.get("pending_decision", {}).get("checkpoint") == "seller_turn":
        notify_seller(session_id, state["pending_decision"])
    elif status in ("awaiting_human", "coordinating", "done") and state.get("negotiation_thread"):
        last = state["negotiation_thread"][-1]
        if last["role"] == "seller":
            verb = {"accept": "accepted your offer", "counter_offer": "sent a counter-offer",
                    "reject": "declined"}.get(last["act"], "replied")
            notify_buyer(session_id, f"Seller {verb} — review ▸")

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
            "status": status,
        })


def _run_graph(thread_id: str, input_or_command, session_id: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = dict(graph.invoke(input_or_command, config=config))

    # Dynamic interrupt() stores its payload in the non-serializable
    # __interrupt__ channel, not in state["pending_decision"]. Bridge it so the
    # frontend (which polls pending_decision) sees the checkpoint, and drop the
    # raw Interrupt object so GET /state stays JSON-serializable.
    interrupts = state.pop("__interrupt__", None)
    if interrupts:
        state["pending_decision"] = interrupts[0].value
        state["status"] = "awaiting_human"

    _sessions[session_id]["last_state"] = state
    _on_state_committed(session_id, state)
    agent_name = {
        "searching": "search", "reviewing": "extract",
        "awaiting_human": "analyst", "negotiating": "negotiate",
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
async def create_session(req: SessionRequest):
    session_id = str(uuid.uuid4())
    thread_id = session_id
    _sessions[session_id] = {"thread_id": thread_id, "last_state": None}

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


@app.get("/deals")
async def read_deals(user_id: int = Depends(_require_user)):
    return store.list_deals(user_id)


@app.get("/deals/{session_id}")
async def read_deal(session_id: str, user_id: int = Depends(_require_user)):
    deal = store.get_deal(session_id)
    if not deal or deal.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


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
