import os, tempfile, importlib
import pytest


@pytest.fixture()
def client(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("ENVOY_DB", tmp.name)
    import app.auth as auth
    importlib.reload(auth)
    auth.init_db()
    import app.store as store
    importlib.reload(store)
    store.init_store()
    import app.main as main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    yield TestClient(main.app)
    os.unlink(tmp.name)


def test_new_user_starts_not_onboarded(client):
    body = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()
    assert body["user"]["onboarded"] is False
