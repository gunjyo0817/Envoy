import os, importlib, datetime
from unittest.mock import patch, MagicMock


def _store_with_token(expiry_iso):
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd)
    os.environ["ENVOY_DB"] = path
    import app.store as store
    importlib.reload(store); store.init_store()
    store.save_google_tokens(1, "old", "refresh-1", expiry_iso, "calendar")
    return store


def test_insert_event_returns_none_on_revoked_token():
    import httpx
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
    store = _store_with_token(future)
    import app.gcal as gcal
    importlib.reload(gcal)
    err = httpx.HTTPStatusError("403", request=MagicMock(), response=MagicMock(status_code=403))
    resp = MagicMock(); resp.raise_for_status.side_effect = err
    with patch("app.gcal.store", store), patch("app.gcal.httpx.post", return_value=resp):
        out = gcal.insert_event(1, "Pick up X", "Marienplatz",
                                "2026-06-20T15:00:00+02:00", "2026-06-20T15:30:00+02:00")
    assert out is None


def test_auth_url_contains_offline_and_scope():
    import app.gcal as gcal
    importlib.reload(gcal)
    url = gcal.auth_url("state-xyz")
    assert "access_type=offline" in url and "prompt=consent" in url
    assert "calendar" in url and "state=state-xyz" in url


def test_valid_access_token_returns_current_when_not_expired():
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
    store = _store_with_token(future)
    import app.gcal as gcal
    importlib.reload(gcal)
    with patch("app.gcal.store", store):
        assert gcal.valid_access_token(1) == "old"


def test_valid_access_token_refreshes_when_expired():
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
    store = _store_with_token(past)
    import app.gcal as gcal
    importlib.reload(gcal)
    resp = MagicMock(); resp.json.return_value = {"access_token": "new", "expires_in": 3600}
    resp.raise_for_status.return_value = None
    with patch("app.gcal.store", store), patch("app.gcal.httpx.post", return_value=resp) as post:
        tok = gcal.valid_access_token(1)
    assert tok == "new"
    assert store.get_google_tokens(1)["access_token"] == "new"
    body = post.call_args[1]["data"]
    assert body["grant_type"] == "refresh_token" and body["refresh_token"] == "refresh-1"
