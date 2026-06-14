import os, tempfile, importlib
from unittest.mock import patch
import pytest


@pytest.fixture()
def client(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("ENVOY_DB", tmp.name)
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "EnvoyTestBot")
    import app.auth as auth; importlib.reload(auth); auth.init_db()
    import app.store as store; importlib.reload(store); store.init_store()
    import app.telegram as tg; importlib.reload(tg)
    import app.main as main; importlib.reload(main)
    from fastapi.testclient import TestClient
    yield TestClient(main.app)
    os.unlink(tmp.name)


def test_link_token_returns_deep_link(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    r = client.post("/telegram/link-token", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith("https://t.me/EnvoyTestBot?start=")
    assert body["token"]


def test_link_token_resolves_to_user(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    token = client.post("/telegram/link-token", headers={"Authorization": f"Bearer {tok}"}).json()["token"]
    import app.telegram as tg
    uid = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["id"]
    assert tg.resolve_link_token(token) == uid


def test_link_token_requires_auth(client):
    assert client.post("/telegram/link-token").status_code == 401
