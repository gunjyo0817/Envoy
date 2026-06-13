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


def test_create_event_inserts_and_returns_link():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.gcal.insert_event", return_value={"htmlLink": "https://cal/evt"}) as ins:
            r = client.post("/calendar/event", json={
                "summary": "Pick up iPhone 14", "location": "Marienplatz",
                "start_iso": "2026-06-20T15:00:00+02:00", "end_iso": "2026-06-20T15:30:00+02:00",
            })
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["htmlLink"] == "https://cal/evt"
    args = ins.call_args[0]
    assert args[0] == 4 and args[1] == "Pick up iPhone 14" and args[2] == "Marienplatz"


def test_create_event_409_when_not_connected():
    main, client = _client()
    main.app.dependency_overrides[main._require_user] = lambda: 4
    try:
        with patch("app.main.gcal.insert_event", return_value=None):
            r = client.post("/calendar/event", json={
                "summary": "x", "location": "y",
                "start_iso": "2026-06-20T15:00:00+02:00", "end_iso": "2026-06-20T15:30:00+02:00"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 409
