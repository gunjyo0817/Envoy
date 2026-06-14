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


def test_complete_onboarding_flips_flag(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    r = client.post("/onboarding/complete", headers=h)
    assert r.status_code == 200
    assert r.json()["onboarded"] is True
    assert client.get("/auth/me", headers=h).json()["onboarded"] is True


def test_complete_onboarding_requires_auth(client):
    assert client.post("/onboarding/complete").status_code == 401
