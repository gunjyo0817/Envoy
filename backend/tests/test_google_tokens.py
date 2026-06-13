import os, tempfile, importlib


def _fresh_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["ENVOY_DB"] = path
    import app.store as store
    importlib.reload(store)
    store.init_store()
    return store


def test_google_tokens_roundtrip_and_refresh_update():
    store = _fresh_store()
    store.save_google_tokens(user_id=3, access_token="a1", refresh_token="r1",
                             expiry="2026-06-13T12:00:00+00:00", scope="calendar")
    tok = store.get_google_tokens(3)
    assert tok["access_token"] == "a1" and tok["refresh_token"] == "r1"
    store.update_google_access(3, access_token="a2", expiry="2026-06-13T13:00:00+00:00")
    tok = store.get_google_tokens(3)
    assert tok["access_token"] == "a2" and tok["refresh_token"] == "r1"  # refresh token preserved


def test_get_google_tokens_missing_returns_none():
    store = _fresh_store()
    assert store.get_google_tokens(999) is None
