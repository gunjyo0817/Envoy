import os, json, datetime
import httpx
import google.generativeai as genai
from langgraph.types import interrupt
from app.state import ProcurementState, PendingDecision


def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


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

def plan_meetup_node(state: ProcurementState) -> dict:
    """Compute the meetup proposal (Gemini + Maps) and COMMIT it to state.

    This node does all the expensive LLM/API work and returns, so the proposal
    is persisted before the interrupt happens in confirm_meetup_node. Because
    LangGraph resumes at the interrupted node (not here), this never re-runs and
    the user sees exactly the proposal that gets finalized.
    """
    idx = state["current_candidate_index"]
    listing = state["ranked_candidates"][idx]
    final_price = state.get("final_price") or listing.get("price_eur", 0)

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
    return {
        "meetup_proposal": meetup_proposal,
        "pending_decision": pending,
        "status": "awaiting_human",
    }


def confirm_meetup_node(state: ProcurementState) -> dict:
    """Human checkpoint 3: pause for the buyer to confirm the planned meetup.

    Cheap gate node (no LLM) so resuming re-runs nothing expensive. Reads the
    already-committed proposal and pending decision from state.
    """
    choice = interrupt(state["pending_decision"])
    if isinstance(choice, dict) and choice.get("action") == "reschedule" and (choice.get("slots") or []):
        slots = choice["slots"]
        pending = {
            "checkpoint": "seller_time",
            "summary": f"Buyer proposes {len(slots)} time(s) to meet. Pick one.",
            "options": [{"id": f"time:{i}", "label": s} for i, s in enumerate(slots)],
            "context": {"slots": slots},
        }
        return {
            "pending_decision": pending, "status": "awaiting_seller",
            "decision_history": state["decision_history"]
                + [{"checkpoint": "confirm_meetup", "choice": "reschedule", "ts": _ts()}],
        }
    if isinstance(choice, dict) and choice.get("action") == "reschedule":
        choice = "reschedule"  # reschedule with no slots → fall back to a fresh re-plan
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    decision_entry = {"checkpoint": "confirm_meetup", "choice": choice, "ts": ts}
    if choice == "cancel":
        return {
            "status": "failed",
            "pending_decision": None,
            "decision_history": state["decision_history"] + [decision_entry],
        }
    if choice == "reschedule":
        # re-plan: route back to plan_meetup for a fresh proposal
        return {
            "pending_decision": None,
            "status": "coordinating",
            "decision_history": state["decision_history"] + [decision_entry],
        }
    # confirm
    return {
        "meetup_proposal": state["meetup_proposal"],
        "confirmed": True,
        "pending_decision": None,
        "decision_history": state["decision_history"] + [decision_entry],
        "status": "done",
    }


def seller_time_turn_node(state: ProcurementState) -> dict:
    """Seller picks one of the buyer's proposed slots (Telegram); re-confirm to buyer."""
    pending = state["pending_decision"]
    slots = pending["context"]["slots"]
    # Loop-guard: only accept a "time:<index>" callback; ignore phase-mismatched
    # taps (e.g. a stale "seller:counter") so they can't silently pick slot 0.
    while True:
        choice = interrupt(pending)
        if isinstance(choice, str) and choice.startswith("time:"):
            break
    idx = 0
    try:
        idx = int(choice.split(":", 1)[1])
    except ValueError:
        idx = 0
    chosen = slots[idx] if 0 <= idx < len(slots) else (slots[0] if slots else None)
    proposal = {**state["meetup_proposal"], "time_suggestion": chosen}
    confirm_pending = {
        "checkpoint": "confirm_meetup",
        "summary": f"Seller agreed to {chosen}. Confirm the meetup?",
        "options": [
            {"id": "confirm", "label": "Confirm meetup"},
            {"id": "reschedule", "label": "Suggest different time"},
            {"id": "cancel", "label": "Cancel"},
        ],
        "context": {"meetup_proposal": proposal},
    }
    return {
        "meetup_proposal": proposal, "pending_decision": confirm_pending,
        "status": "awaiting_human",
        "decision_history": state["decision_history"]
            + [{"checkpoint": "seller_time", "choice": choice, "ts": _ts()}],
    }
