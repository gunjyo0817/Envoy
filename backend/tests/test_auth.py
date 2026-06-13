import os, tempfile, importlib
import pytest

@pytest.fixture()
def client(monkeypatch):
    # Fresh temp DB per test
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("ENVOY_DB", tmp.name)
    import app.auth as auth
    importlib.reload(auth)
    auth.init_db()
    # main imports auth symbols at module load; reload so it binds the reloaded module
    import app.main as main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    c = TestClient(main.app)
    yield c
    os.unlink(tmp.name)

def test_signup_returns_token_and_user(client):
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw123", "name": "Ann"})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body and body["user"]["email"] == "a@b.com"
    assert body["user"]["language"] == "en"

def test_duplicate_email_rejected(client):
    client.post("/auth/signup", json={"email": "a@b.com", "password": "pw123"})
    r = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw123"})
    assert r.status_code == 409

def test_login_wrong_password_401(client):
    client.post("/auth/signup", json={"email": "a@b.com", "password": "right"})
    r = client.post("/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r.status_code == 401

def test_login_success_then_settings_roundtrip(client):
    client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"})
    tok = client.post("/auth/login", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/settings", headers=h).json()["language"] == "en"
    r = client.put("/settings", headers=h, json={"language": "de", "default_address": "München"})
    assert r.json() == {"language": "de", "default_address": "München"}
    assert client.get("/settings", headers=h).json()["default_address"] == "München"

def test_settings_requires_auth(client):
    assert client.get("/settings").status_code == 401
