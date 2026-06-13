import os, json, datetime
import google.generativeai as genai
from langgraph.types import interrupt
from app.state import ProcurementState, PendingDecision, NegotiationMessage
from app.agents.extract import classify_message
from app.mock.seller import mock_seller_response


def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


_LANG_NAME = {"en": "English", "de": "German"}


def _lang_name(code: str) -> str:
    return _LANG_NAME.get(code, "English")


def _gemini_opening_offer(listing: dict, budget: float, language: str = "en") -> dict:
    """Returns {offer_price: float, message_text: str}"""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    listing_price = listing.get("price_eur", budget)
    prompt = (
        f"You are a buyer's agent. Listing price: €{listing_price}. Your max budget: €{budget}. "
        f"Suggest a strategic opening offer (80-90% of listing price) and write a short, polite "
        f"message to the seller in {_lang_name(language)}. "
        f"Return JSON only: {{\"offer_price\": float, \"message_text\": str}}"
    )
    text = model.generate_content(prompt).text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)


def _gemini_counter_response(thread: list, budget: float, seller_price: float,
                             suggested_counter: float, language: str = "en") -> dict:
    """Returns {message_text: str, recommendation: str}"""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    history = "\n".join([f"{m['role']}: {m['text']}" for m in thread[-4:]])
    prompt = (
        f"The seller countered at €{seller_price}; your budget is €{budget}. "
        f"You will counter back at €{suggested_counter:.0f}. Recent messages:\n{history}\n"
        f"Write a short, polite message to the seller in {_lang_name(language)} proposing €{suggested_counter:.0f}, "
        f"and give your recommendation. "
        f"Return JSON: {{\"message_text\": str, \"recommendation\": \"accept\"|\"counter\"|\"walk_away\"}}"
    )
    text = model.generate_content(prompt).text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)


def _listing_price(state: ProcurementState) -> float:
    listing = state["ranked_candidates"][state["current_candidate_index"]]
    return listing.get("price_eur") or state["budget_max"]


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


# ── Round 1 ─────────────────────────────────────────────────────────────────

def make_offer_node(state: ProcurementState) -> dict:
    """Compute the opening offer and commit it to the thread before pausing.

    Runs the Gemini call here (not in the interrupt node) so resuming never
    re-generates a different offer. Resets the thread for a fresh candidate.
    """
    degraded = list(state.get("degraded", []))
    idx = state["current_candidate_index"]
    candidates = state["ranked_candidates"]
    if idx >= len(candidates):
        return {"status": "failed", "degraded": degraded}

    listing = candidates[idx]
    listing_price = listing.get("price_eur") or state["budget_max"]

    offer_data = _gemini_opening_offer(listing, state["budget_max"], state.get("language", "en"))
    offer_price = offer_data.get("offer_price") or round(listing_price * 0.85)
    buyer_msg: NegotiationMessage = {
        "role": "buyer", "text": offer_data["message_text"],
        "act": "initial_offer", "price": float(offer_price), "ts": _ts(),
    }

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
    return {
        "negotiation_thread": [buyer_msg],
        "pending_decision": pending,
        "status": "awaiting_human",
        "degraded": list(set(degraded)),
    }


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
        # Loop-guard: ignore phase-mismatched callbacks (e.g. a stale "time:N" tap
        # from a reschedule) so they can't fall through to a silent counter-offer.
        while True:
            choice = interrupt(state["pending_decision"])
            if isinstance(choice, str) and (
                choice in ("accept", "reject", "counter") or choice.startswith("counter:")
            ):
                break
    else:
        ctx = state["pending_decision"]["context"]
        reply = mock_seller_response(ctx["listing_price"], ctx["buyer_offer"])
        choice = {"accept": "accept", "reject": "reject",
                  "counter_offer": "counter"}.get(reply["act"], "counter")
    return _apply_seller_choice(state, choice)


# ── Round 2 (seller counter) ─────────────────────────────────────────────────

def make_counter_node(state: ProcurementState) -> dict:
    """Compute the counter recommendation and commit it before pausing."""
    degraded = list(state.get("degraded", []))
    listing_price = _listing_price(state)
    thread = list(state["negotiation_thread"])
    language = state.get("language", "en")

    last_seller = next((m for m in reversed(thread) if m["role"] == "seller"), None)
    seller_price = (last_seller.get("price") if last_seller else None) or listing_price
    buyer_last = next((m["price"] for m in reversed(thread)
                       if m["role"] == "buyer" and m.get("price") is not None), None)

    # Counter strictly between the buyer's last offer and the seller's ask.
    if buyer_last is not None and buyer_last < seller_price:
        suggested = round((buyer_last + seller_price) / 2)
        suggested = max(buyer_last + 1, min(suggested, seller_price - 1))
    else:
        suggested = max(round(seller_price - 5), 1)

    counter_data = _gemini_counter_response(thread, state["budget_max"], seller_price, suggested, language)

    pending: PendingDecision = {
        "checkpoint": "confirm_offer",
        "summary": (f"Seller countered at €{seller_price:.0f}. "
                    f"Agent recommends: {counter_data.get('recommendation', 'counter')}"),
        "options": [
            {"id": "accept", "label": f"Accept €{seller_price:.0f}"},
            {"id": "counter", "label": f"Counter at €{suggested:.0f}"},
            {"id": "skip", "label": "Walk away"},
        ],
        "context": {"seller_price": seller_price, "suggested_counter": suggested, "counter_data": counter_data},
    }
    return {
        "pending_decision": pending,
        "status": "awaiting_human",
        "degraded": list(set(degraded)),
    }


def decide_counter_node(state: ProcurementState) -> dict:
    """Pause for the counter decision, then resolve the deal."""
    degraded = list(state.get("degraded", []))
    idx = state["current_candidate_index"]
    listing_price = _listing_price(state)
    thread = list(state["negotiation_thread"])
    pending = state["pending_decision"]
    seller_price = pending["context"]["seller_price"]
    counter_data = pending["context"]["counter_data"]
    suggested_counter = pending["context"]["suggested_counter"]

    choice = interrupt(pending)
    entry = {"checkpoint": "confirm_offer", "choice": choice, "ts": _ts()}
    history = state["decision_history"] + [entry]
    base = {
        "negotiation_thread": thread, "decision_history": history,
        "degraded": list(set(degraded)), "pending_decision": None,
    }

    if choice == "accept":
        return {**base, "final_price": float(seller_price), "status": "coordinating"}
    if choice == "skip":
        return {**base, "negotiation_thread": [],
                "current_candidate_index": idx + 1, "status": "negotiating"}

    # counter back → hand to the seller again (async/real), do NOT auto-close
    counter_price = suggested_counter
    buyer_counter: NegotiationMessage = {
        "role": "buyer", "text": counter_data["message_text"],
        "act": "counter_offer", "price": float(counter_price), "ts": _ts(),
    }
    thread.append(buyer_counter)
    suggestion = _gemini_seller_suggestion(listing_price, counter_price, state.get("language", "en"))
    seller_pending: PendingDecision = {
        "checkpoint": "seller_turn",
        "summary": f"Buyer counters at €{counter_price:.0f} (listed €{listing_price:.0f}). Reply?",
        "options": [
            {"id": "accept", "label": f"Accept €{counter_price:.0f}"},
            {"id": "counter", "label": f"Counter €{suggestion['counter_price']:.0f}"},
            {"id": "reject", "label": "Reject"},
        ],
        "context": {
            "buyer_offer": float(counter_price), "listing_price": float(listing_price),
            "suggested_counter": float(suggestion["counter_price"]),
            "draft_text": suggestion["message_text"],
        },
    }
    return {**base, "negotiation_thread": thread,
            "pending_decision": seller_pending, "status": "awaiting_seller"}
