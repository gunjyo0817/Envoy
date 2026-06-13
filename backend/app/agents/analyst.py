import os, json, datetime
import google.generativeai as genai
from langgraph.types import interrupt
from app.state import ProcurementState, PendingDecision

_CONDITION_SCORE = {
    "new": 1.0, "like_new": 0.95, "very_good": 0.85,
    "good": 0.70, "acceptable": 0.50,
}

def score_listing(listing: dict, budget_min: float, budget_max: float) -> float:
    price = listing.get("price_eur") or budget_max
    span = max(budget_max - budget_min, 1.0)
    price_score = max(0.0, min(1.0, (budget_max - price) / span))
    condition_score = _CONDITION_SCORE.get(listing.get("condition", "good"), 0.5)
    rating = listing.get("seller_rating") or 3.0
    reviews = min(listing.get("seller_reviews") or 0, 50)
    trust_score = (rating / 5.0) * 0.7 + (reviews / 50) * 0.3
    dist = listing.get("distance_km") or 15.0
    distance_score = max(0.0, 1.0 - dist / 20.0)
    return (price_score * 0.40 + condition_score * 0.30 +
            trust_score * 0.20 + distance_score * 0.10)

def rank_candidates(listings: list[dict], budget_min: float, budget_max: float) -> list[dict]:
    scored = [{**l, "score": round(score_listing(l, budget_min, budget_max) * 100)} for l in listings]
    return sorted(scored, key=lambda x: x["score"], reverse=True)

def _gemini_insight(candidate: dict, budget: float) -> str:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        f"You are a buyer's agent. In one short sentence (max 15 words), explain why "
        f"this listing is a good or bad deal. Budget: €{budget}. "
        f"Listing: {json.dumps(candidate)}"
    )
    return model.generate_content(prompt).text.strip()

def analyst_node(state: ProcurementState) -> dict:
    bmin, bmax = state["budget_min"], state["budget_max"]
    in_budget = [
        l for l in state["structured_listings"]
        if bmin <= (l.get("price_eur") or 0) <= bmax
    ]
    ranked = rank_candidates(in_budget, bmin, bmax)[:5]

    top = ranked[0] if ranked else {}
    insight = _gemini_insight(top, bmax) if top else "No matching listings found."

    if ranked:
        ranked[0]["insight"] = insight

    pending: PendingDecision = {
        "checkpoint": "confirm_candidate",
        "summary": f"Found {state['query']} from €{top.get('price_eur', '?')} — start negotiating?",
        "options": [
            {"id": "approve", "label": "Yes, go for #1"},
            {"id": "pick_2", "label": "Show me #2 instead"},
            {"id": "cancel", "label": "Cancel search"},
        ],
        "context": {"ranked_candidates": ranked},
    }
    return {
        "ranked_candidates": ranked,
        "pending_decision": pending,
        "status": "awaiting_human",
    }


def confirm_candidate_node(state: ProcurementState) -> dict:
    """Human checkpoint 1: pause for the buyer to approve the top candidate.

    Cheap gate node (no LLM) so resuming re-runs nothing expensive. Routes the
    buyer's choice without polluting the analyst's ranking work.
    """
    if not state["ranked_candidates"]:
        return {"status": "failed", "pending_decision": None}

    choice = interrupt(state["pending_decision"])
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry = {"checkpoint": "confirm_candidate", "choice": choice, "ts": ts}
    base = {
        "pending_decision": None,
        "decision_history": state["decision_history"] + [entry],
    }

    if choice == "cancel":
        return {**base, "status": "failed"}
    if choice == "pick_2":
        return {**base, "current_candidate_index": 1, "status": "negotiating"}
    return {**base, "status": "negotiating"}
