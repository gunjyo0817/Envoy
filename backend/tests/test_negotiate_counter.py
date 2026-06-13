from unittest.mock import patch
from app.agents.negotiate import make_counter_node


def test_counter_is_between_buyer_offer_and_seller_price():
    state = {
        "current_candidate_index": 0,
        "ranked_candidates": [{"price_eur": 200.0}],
        "budget_max": 250.0,
        "language": "en",
        "negotiation_thread": [
            {"role": "buyer", "text": "offer", "act": "initial_offer", "price": 165.0, "ts": "t"},
            {"role": "seller", "text": "I'll do 179", "act": "counter_offer", "price": 179.0, "ts": "t"},
        ],
        "degraded": [],
    }
    with patch("app.agents.negotiate._gemini_counter_response",
               return_value={"message_text": "How about 172?", "recommendation": "counter"}):
        out = make_counter_node(state)
    ctx = out["pending_decision"]["context"]
    assert 165.0 < ctx["suggested_counter"] < 179.0   # strictly between
    assert ctx["suggested_counter"] == 172            # midpoint of 165 and 179
