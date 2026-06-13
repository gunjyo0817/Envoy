from unittest.mock import patch
from app.agents.coordinate import confirm_meetup_node, seller_time_turn_node
from app.graph import _after_confirm_meetup, _after_seller_time_turn


def _state():
    return {
        "meetup_proposal": {"location": "Marienplatz", "time_suggestion": "Sat afternoon",
                            "final_price": 170, "buyer_route": {"duration_text": "15 min"},
                            "seller_location": "Schwabing"},
        "pending_decision": {"checkpoint": "confirm_meetup", "summary": "", "options": [], "context": {}},
        "decision_history": [], "status": "awaiting_human",
    }


def test_structured_reschedule_routes_to_seller_time():
    st = _state()
    with patch("app.agents.coordinate.interrupt",
               return_value={"action": "reschedule", "slots": ["2026-06-20T15:00:00+02:00"]}):
        out = confirm_meetup_node(st)
    assert out["status"] == "awaiting_seller"
    assert out["pending_decision"]["checkpoint"] == "seller_time"
    assert out["pending_decision"]["context"]["slots"] == ["2026-06-20T15:00:00+02:00"]
    assert _after_confirm_meetup(out) == "seller_time_turn"


def test_seller_time_turn_sets_concrete_time_and_reconfirms():
    st = _state()
    st["pending_decision"] = {"checkpoint": "seller_time", "summary": "", "options": [],
                              "context": {"slots": ["2026-06-20T15:00:00+02:00", "2026-06-21T11:00:00+02:00"]}}
    with patch("app.agents.coordinate.interrupt", return_value="time:1"):
        out = seller_time_turn_node(st)
    assert out["meetup_proposal"]["time_suggestion"] == "2026-06-21T11:00:00+02:00"
    assert out["pending_decision"]["checkpoint"] == "confirm_meetup"
    assert out["status"] == "awaiting_human"
    assert _after_seller_time_turn(out) == "confirm_meetup"
