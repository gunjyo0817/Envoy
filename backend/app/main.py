import uuid, asyncio, os
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
    for log in get_logs(session_id):
        await websocket.send_json(log)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(session_id, send_fn)
