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
