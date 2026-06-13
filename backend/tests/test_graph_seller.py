from app.graph import _after_decide_offer, _after_seller_turn


def test_after_decide_offer_routes_to_seller_turn():
    assert _after_decide_offer({"status": "awaiting_seller", "negotiation_thread": []}) == "seller_turn"


def test_after_decide_offer_skip_retries_candidate():
    assert _after_decide_offer({"status": "negotiating", "negotiation_thread": []}) == "make_offer"


def test_after_seller_turn_accept_to_meetup():
    assert _after_seller_turn({"status": "coordinating", "negotiation_thread": []}) == "plan_meetup"


def test_after_seller_turn_counter_to_round2():
    state = {"status": "negotiating",
             "negotiation_thread": [{"role": "seller", "act": "counter_offer", "price": 185.0}]}
    assert _after_seller_turn(state) == "make_counter"


def test_after_seller_turn_reject_next_candidate():
    assert _after_seller_turn({"status": "negotiating", "negotiation_thread": []}) == "make_offer"
