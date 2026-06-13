import importlib
from unittest.mock import patch


def test_on_state_committed_records_thread_and_user():
    import app.main as main
    importlib.reload(main)
    main._sessions["sess"] = {"thread_id": "sess", "last_state": None, "user_id": 5}
    captured = {}
    with patch("app.main.store.record_deal", lambda deal: captured.update(deal)):
        state = {
            "status": "done", "query": "iPhone 14", "final_price": 170.0,
            "ranked_candidates": [{"image_url": "http://img", "title": "iPhone 14"}],
            "current_candidate_index": 0,
            "negotiation_thread": [{"role": "seller", "text": "OK", "act": "accept", "price": 170.0, "ts": "t"}],
            "meetup_proposal": {"location": "Marienplatz"},
        }
        main._on_state_committed("sess", state)
    assert captured["user_id"] == 5
    assert captured["negotiation_thread"][-1]["act"] == "accept"
    assert captured["final_price"] == 170.0
