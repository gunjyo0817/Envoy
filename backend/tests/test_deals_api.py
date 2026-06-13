from fastapi.testclient import TestClient
from unittest.mock import patch
import app.main as main


def test_list_deals_returns_rows_for_user():
    client = TestClient(main.app)
    main.app.dependency_overrides[main._require_user] = lambda: 7
    try:
        with patch("app.main.store.list_deals", return_value=[{"session_id": "s-1", "final_price": 180.0}]):
            resp = client.get("/deals")
    finally:
        main.app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()[0]["session_id"] == "s-1"


def test_get_deal_404_when_not_owner():
    client = TestClient(main.app)
    main.app.dependency_overrides[main._require_user] = lambda: 7
    try:
        with patch("app.main.store.get_deal", return_value={"session_id": "s-9", "user_id": 99}):
            resp = client.get("/deals/s-9")
    finally:
        main.app.dependency_overrides.clear()
    assert resp.status_code == 404
