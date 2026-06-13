import importlib
from unittest.mock import patch
from fastapi.testclient import TestClient


def _client():
    import app.main as main
    importlib.reload(main)
    return main, TestClient(main.app)


def test_auth_url_requires_user_and_returns_url():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.gcal.auth_url", lambda state: f"https://google/auth?state={state}"):
            r = client.get("/calendar/auth-url")
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://google/auth?state=")
    state = r.json()["url"].split("state=")[1]
    assert main._oauth_states[state] == 4


def test_status_reports_connected():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.store.get_google_tokens", return_value={"access_token": "a"}):
            r = client.get("/calendar/status")
    finally:
        main.app.dependency_overrides.clear()
    assert r.json() == {"connected": True}
