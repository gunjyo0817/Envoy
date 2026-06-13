from __future__ import annotations
from typing import Literal, TypedDict


class PendingDecision(TypedDict):
    checkpoint: str
    summary: str
    options: list[dict]
    context: dict


class NegotiationMessage(TypedDict):
    role: Literal["buyer", "seller"]
    text: str
    act: Literal["initial_offer", "counter_offer", "accept", "reject", "question", "stall"]
    price: float | None
    ts: str


class ProcurementState(TypedDict):
    # Input
    query: str
    budget: float
    condition: str
    location: str
    max_distance_km: int
    # Search
    raw_listings: list[dict]
    structured_listings: list[dict]
    # Analysis
    ranked_candidates: list[dict]
    current_candidate_index: int
    # Negotiation
    negotiation_thread: list[NegotiationMessage]
    final_price: float | None
    # Coordination
    meetup_proposal: dict | None
    confirmed: bool
    # Human-in-the-loop
    pending_decision: PendingDecision | None
    decision_history: list[dict]
    human_feedback: str | None
    # Control
    status: Literal[
        "searching", "reviewing", "awaiting_human",
        "negotiating", "coordinating", "done", "failed"
    ]
    degraded: list[str]


def initial_state(
    query: str, budget: float, condition: str, location: str, max_distance_km: int
) -> ProcurementState:
    return {
        "query": query, "budget": budget, "condition": condition,
        "location": location, "max_distance_km": max_distance_km,
        "raw_listings": [], "structured_listings": [],
        "ranked_candidates": [], "current_candidate_index": 0,
        "negotiation_thread": [], "final_price": None,
        "meetup_proposal": None, "confirmed": False,
        "pending_decision": None, "decision_history": [],
        "human_feedback": None,
        "status": "searching", "degraded": [],
    }
