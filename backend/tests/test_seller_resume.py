import importlib
from unittest.mock import patch


def test_awaiting_seller_triggers_notify(monkeypatch):
    monkeypatch.setenv("LIVE_SELLER", "true")
    import app.main as main
    importlib.reload(main)
    captured = {}

    def fake_notify(session_id, pending):
        captured["session_id"] = session_id
        captured["checkpoint"] = pending["checkpoint"]

    with patch("app.main.notify_seller", fake_notify):
        main._sessions["sess"] = {"thread_id": "sess", "last_state": None}
        state = {"status": "awaiting_seller",
                 "pending_decision": {"checkpoint": "seller_turn",
                                      "context": {"buyer_offer": 1, "suggested_counter": 1}}}
        main._on_state_committed("sess", state)
    assert captured["session_id"] == "sess"
    assert captured["checkpoint"] == "seller_turn"
