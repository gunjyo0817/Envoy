import os
from unittest.mock import patch
from app.agents.negotiate import decide_offer_node, seller_turn_node


def _state(buyer_price=170.0, listing=200.0):
    return {
        "current_candidate_index": 0,
        "ranked_candidates": [{"price_eur": listing, "title": "iPhone 14"}],
        "budget_max": 250.0,
        "language": "en",
        "negotiation_thread": [
            {"role": "buyer", "text": "offer", "act": "initial_offer", "price": buyer_price, "ts": "t"},
        ],
        "decision_history": [],
        "degraded": [],
        "pending_decision": {
            "checkpoint": "confirm_offer",
            "summary": "", "options": [],
            "context": {"offer_price": buyer_price, "listing_price": listing},
        },
    }


def test_decide_offer_approve_routes_to_seller_and_sets_awaiting():
    with patch("app.agents.negotiate.interrupt", return_value="approve"), \
         patch("app.agents.negotiate._gemini_seller_suggestion",
               return_value={"counter_price": 185.0, "message_text": "How about 185?"}):
        out = decide_offer_node(_state())
    assert out["status"] == "awaiting_seller"
    assert out["pending_decision"]["checkpoint"] == "seller_turn"
    assert out["pending_decision"]["context"]["buyer_offer"] == 170.0
    assert out["pending_decision"]["context"]["suggested_counter"] == 185.0


def test_decide_offer_skip_advances_candidate():
    with patch("app.agents.negotiate.interrupt", return_value="skip"):
        out = decide_offer_node(_state())
    assert out["current_candidate_index"] == 1
    assert out["status"] == "negotiating"


def test_seller_turn_mock_accept_when_offer_high(monkeypatch):
    monkeypatch.delenv("LIVE_SELLER", raising=False)  # mock path
    st = _state(buyer_price=195.0, listing=200.0)  # >= 95% -> accept
    st["pending_decision"] = {
        "checkpoint": "seller_turn", "summary": "", "options": [],
        "context": {"buyer_offer": 195.0, "listing_price": 200.0, "suggested_counter": 190.0},
    }
    out = seller_turn_node(st)
    assert out["status"] == "coordinating"
    assert out["final_price"] == 195.0
    assert out["negotiation_thread"][-1]["role"] == "seller"
    assert out["negotiation_thread"][-1]["act"] == "accept"


def test_seller_turn_live_counter(monkeypatch):
    monkeypatch.setenv("LIVE_SELLER", "true")
    st = _state(buyer_price=170.0, listing=200.0)
    st["pending_decision"] = {
        "checkpoint": "seller_turn", "summary": "", "options": [],
        "context": {"buyer_offer": 170.0, "listing_price": 200.0, "suggested_counter": 185.0,
                    "draft_text": "How about 185?"},
    }
    with patch("app.agents.negotiate.interrupt", return_value="counter"):
        out = seller_turn_node(st)
    assert out["status"] == "negotiating"
    last = out["negotiation_thread"][-1]
    assert last["role"] == "seller" and last["act"] == "counter_offer" and last["price"] == 185.0
