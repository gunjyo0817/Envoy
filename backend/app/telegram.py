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
            f"Agent suggests countering at €{counter:.0f}:\n\"{ctx.get('draft_text', '')}\"")
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
