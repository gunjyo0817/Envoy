import importlib
from unittest.mock import patch, MagicMock


def test_bridge_preserves_awaiting_seller_and_notifies():
    import app.main as main
    importlib.reload(main)

    seller_pending = {"checkpoint": "seller_turn",
                      "context": {"buyer_offer": 170.0, "suggested_counter": 185.0}}
    fake_interrupt = MagicMock()
    fake_interrupt.value = seller_pending
    fake_graph = MagicMock()
    # graph.invoke returns a state dict carrying the __interrupt__ channel
    fake_graph.invoke.return_value = {"status": "negotiating", "__interrupt__": [fake_interrupt],
                                      "negotiation_thread": []}

    main._sessions["sess"] = {"thread_id": "sess", "last_state": None}
    captured = {}
    with patch("app.main.get_graph", return_value=fake_graph), \
         patch("app.main.notify_seller", lambda sid, pending: captured.update(sid=sid, cp=pending["checkpoint"])):
        out = main._run_graph("sess", {}, "sess")

    assert out["status"] == "awaiting_seller"
    assert out["pending_decision"]["checkpoint"] == "seller_turn"
    assert captured == {"sid": "sess", "cp": "seller_turn"}


def test_bridge_keeps_awaiting_human_for_buyer_checkpoint():
    import app.main as main
    importlib.reload(main)

    buyer_pending = {"checkpoint": "confirm_offer", "context": {}}
    fake_interrupt = MagicMock()
    fake_interrupt.value = buyer_pending
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {"status": "negotiating", "__interrupt__": [fake_interrupt],
                                      "negotiation_thread": []}
    main._sessions["sess2"] = {"thread_id": "sess2", "last_state": None}
    with patch("app.main.get_graph", return_value=fake_graph):
        out = main._run_graph("sess2", {}, "sess2")
    assert out["status"] == "awaiting_human"
