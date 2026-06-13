import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_post_session_returns_session_id():
    with patch("app.main.get_graph") as mock_graph:
        mock_graph.return_value.invoke.return_value = {
            "status": "awaiting_human",
            "pending_decision": {
                "checkpoint": "confirm_candidate",
                "summary": "Found iPhone",
                "options": [{"id": "approve", "label": "Yes"}],
                "context": {}
            },
            "degraded": [],
        }
        from app.main import app
        client = TestClient(app)
        resp = client.post("/session", json={
            "query": "iPhone 14", "budget": 200.0,
            "condition": "good+", "location": "München", "max_distance_km": 15
        })
    assert resp.status_code == 200
    assert "session_id" in resp.json()

def test_get_state_returns_404_for_unknown_session():
    from app.main import app
    client = TestClient(app)
    resp = client.get("/session/nonexistent/state")
    assert resp.status_code == 404
