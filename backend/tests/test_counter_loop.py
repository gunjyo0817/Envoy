import os
from unittest.mock import patch
from app.agents.negotiate import decide_counter_node
from app.graph import _after_decide_counter


def _counter_state():
    return {
        "current_candidate_index": 0,
        "ranked_candidates": [{"price_eur": 200.0, "title": "iPhone 14"}],
        "budget_max": 250.0, "language": "en",
        "negotiation_thread": [
            {"role": "buyer", "text": "o", "act": "initial_offer", "price": 165.0, "ts": "t"},
            {"role": "seller", "text": "179", "act": "counter_offer", "price": 179.0, "ts": "t"},
        ],
        "decision_history": [], "degraded": [],
        "pending_decision": {
            "checkpoint": "confirm_offer", "summary": "", "options": [],
            "context": {"seller_price": 179.0, "suggested_counter": 172.0,
                        "counter_data": {"message_text": "How about 172?", "recommendation": "counter"}},
        },
    }


def test_counter_routes_to_seller_turn_not_autoclose():
    with patch("app.agents.negotiate.interrupt", return_value="counter"), \
         patch("app.agents.negotiate._gemini_seller_suggestion",
               return_value={"counter_price": 175.0, "message_text": "Treffen wir uns bei 175?"}):
        out = decide_counter_node(_counter_state())
    # Must hand back to the seller, NOT close the deal.
    assert out["status"] == "awaiting_seller"
    assert "final_price" not in out or out.get("final_price") is None
    assert out["pending_decision"]["checkpoint"] == "seller_turn"
    assert out["pending_decision"]["context"]["buyer_offer"] == 172.0  # the buyer's counter price
    # the buyer's counter is committed to the thread
    assert out["negotiation_thread"][-1]["role"] == "buyer"
    assert out["negotiation_thread"][-1]["price"] == 172.0
    assert _after_decide_counter(out) == "seller_turn"


def test_counter_accept_still_closes():
    with patch("app.agents.negotiate.interrupt", return_value="accept"):
        out = decide_counter_node(_counter_state())
    assert out["status"] == "coordinating" and out["final_price"] == 179.0
