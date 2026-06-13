from app.state import ProcurementState, PendingDecision, NegotiationMessage, initial_state

def test_initial_state_has_required_keys():
    s = initial_state("iPhone 14", 200.0, "good+", "München", 15)
    assert s["query"] == "iPhone 14"
    assert s["budget"] == 200.0
    assert s["status"] == "searching"
    assert s["degraded"] == []
    assert s["decision_history"] == []
    assert s["current_candidate_index"] == 0
    assert s["confirmed"] is False
    assert s["pending_decision"] is None
    assert s["final_price"] is None

def test_pending_decision_has_required_fields():
    pd: PendingDecision = {
        "checkpoint": "confirm_candidate",
        "summary": "Found iPhone 14 at €175",
        "options": [{"id": "approve", "label": "Go for it"}],
        "context": {}
    }
    assert pd["checkpoint"] == "confirm_candidate"

def test_negotiation_message_has_required_fields():
    msg: NegotiationMessage = {
        "role": "buyer",
        "text": "I offer €160",
        "act": "initial_offer",
        "price": 160.0,
        "ts": "2026-06-13T10:00:00"
    }
    assert msg["act"] == "initial_offer"
