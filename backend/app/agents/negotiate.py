import os, json, datetime
import google.generativeai as genai
from langgraph.types import interrupt
from app.state import ProcurementState, PendingDecision, NegotiationMessage
from app.agents.extract import classify_message
from app.mock.seller import mock_seller_response


def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


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


def _listing_price(state: ProcurementState) -> float:
    listing = state["ranked_candidates"][state["current_candidate_index"]]
    return listing.get("price_eur") or state["budget"]


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
    listing_price = listing.get("price_eur") or state["budget"]

    offer_data = _gemini_opening_offer(listing, state["budget"])
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
    """Pause for the opening-offer decision, then simulate the seller reply.

    The seller simulation runs *after* the single interrupt, so the node
    completes and commits the seller message — nothing re-generates on resume.
    """
    degraded = list(state.get("degraded", []))
    idx = state["current_candidate_index"]
    listing_price = _listing_price(state)
    thread = list(state["negotiation_thread"])

    choice = interrupt(state["pending_decision"])
    entry = {"checkpoint": "confirm_offer", "choice": choice, "ts": _ts()}
    history = state["decision_history"] + [entry]

    if choice == "skip":
        return {
            "negotiation_thread": [], "current_candidate_index": idx + 1,
            "decision_history": history, "status": "negotiating",
            "pending_decision": None,
        }

    offer_price = thread[-1]["price"]
    if choice == "lower":
        offer_price = round(listing_price * 0.78)
        thread[-1] = {**thread[-1], "price": float(offer_price),
                      "text": f"Würden Sie €{offer_price:.0f} akzeptieren?"}

    seller_reply = mock_seller_response(listing_price, offer_price)
    # Classification runs for the GLiNER2 eval + degraded story, but the mock
    # seller already carries authoritative act/price — trust those, fall back to
    # the classifier only when a field is missing (e.g. real Tavily sellers).
    classified = classify_message(seller_reply["text"], record_degraded=degraded)
    seller_reply = {
        **seller_reply,
        "act": seller_reply.get("act") or classified.get("act", "stall"),
        "price": seller_reply["price"] if seller_reply.get("price") is not None
                 else classified.get("price"),
    }
    thread.append(seller_reply)

    base = {
        "negotiation_thread": thread, "decision_history": history,
        "degraded": list(set(degraded)), "pending_decision": None,
    }
    if seller_reply["act"] == "accept":
        return {**base, "final_price": float(offer_price), "status": "coordinating"}
    if seller_reply["act"] == "reject":
        return {**base, "negotiation_thread": [],
                "current_candidate_index": idx + 1, "status": "negotiating"}
    # counter / stall / question — seller is still negotiating, go to round 2
    return {**base, "status": "negotiating"}


# ── Round 2 (seller counter) ─────────────────────────────────────────────────

def make_counter_node(state: ProcurementState) -> dict:
    """Compute the counter recommendation and commit it before pausing."""
    degraded = list(state.get("degraded", []))
    listing_price = _listing_price(state)
    thread = list(state["negotiation_thread"])

    last_seller = next((m for m in reversed(thread) if m["role"] == "seller"), None)
    seller_price = (last_seller.get("price") if last_seller else None) or listing_price
    counter_data = _gemini_counter_response(thread, state["budget"], seller_price)

    pending: PendingDecision = {
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

    # counter back, then resolve with one more seller turn
    counter_price = counter_data.get("offer_price") or (seller_price - 5)
    buyer_counter: NegotiationMessage = {
        "role": "buyer", "text": counter_data["message_text"],
        "act": "counter_offer", "price": float(counter_price), "ts": _ts(),
    }
    thread.append(buyer_counter)
    seller_final = mock_seller_response(listing_price, counter_price)
    classified = classify_message(seller_final["text"], record_degraded=degraded)
    seller_final = {
        **seller_final,
        "act": seller_final.get("act") or classified.get("act", "stall"),
        "price": seller_final["price"] if seller_final.get("price") is not None
                 else classified.get("price"),
    }
    thread.append(seller_final)
    final_price = counter_price if seller_final["act"] == "accept" else seller_price

    return {**base, "negotiation_thread": thread,
            "final_price": float(final_price), "status": "coordinating"}
