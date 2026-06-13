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
    listing_price = listing.get("price_eur") or state["budget"]
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
        return {"negotiation_thread": [],
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
