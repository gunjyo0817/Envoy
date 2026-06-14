import os, tempfile, importlib
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def _store_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("ENVOY_DB", tmp.name)
    import app.store as store; importlib.reload(store); store.init_store()
    yield
    os.unlink(tmp.name)


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


@pytest.mark.asyncio
async def test_start_with_token_binds_chat_to_user():
    import app.telegram as tg
    import app.store as store
    uid = 77
    token = tg.mint_link_token(uid)["token"]
    upd = {"message": {"chat": {"id": 9001}, "text": f"/start {token}"}}
    with patch("app.telegram.tg_send"):
        await tg._dispatch(upd, on_seller_reply=lambda *a: None)
    assert store.resolve_chat(9001)["user_id"] == uid
    assert store.resolve_chat(9001)["role"] == "buyer"


@pytest.mark.asyncio
async def test_start_seller_still_role_based():
    import app.telegram as tg
    import app.store as store
    upd = {"message": {"chat": {"id": 9002}, "text": "/start seller"}}
    with patch("app.telegram.tg_send"):
        await tg._dispatch(upd, on_seller_reply=lambda *a: None)
    assert store.resolve_chat(9002)["role"] == "seller"


def test_chat_for_user_returns_bound_chat():
    import app.store as store
    store.register_chat(5005, "buyer", user_id=42)
    assert store.chat_for_user(42) == 5005
    assert store.chat_for_user(999) is None


def test_notify_buyer_routes_to_user_chat(monkeypatch):
    import app.telegram as tg
    import app.store as store
    store.register_chat(6006, "buyer", user_id=42)
    sent = {}
    monkeypatch.setattr(tg, "tg_send", lambda chat_id, text, buttons=None: sent.update(chat_id=chat_id, text=text))
    tg.notify_buyer("sess-1", "Seller replied — review", user_id=42)
    assert sent["chat_id"] == 6006


def test_notify_buyer_falls_back_to_role(monkeypatch):
    import app.telegram as tg
    import app.store as store
    store.register_chat(7007, "buyer")  # no user_id
    sent = {}
    monkeypatch.setattr(tg, "tg_send", lambda chat_id, text, buttons=None: sent.update(chat_id=chat_id))
    tg.notify_buyer("sess-2", "msg", user_id=None)
    assert sent["chat_id"] == 7007


def test_telegram_status_reflects_binding(client):
    tok = client.post("/auth/signup", json={"email": "a@b.com", "password": "pw"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/telegram/status", headers=h).json()["connected"] is False
    uid = client.get("/auth/me", headers=h).json()["id"]
    import app.store as store
    store.register_chat(8008, "buyer", user_id=uid)
    assert client.get("/telegram/status", headers=h).json()["connected"] is True
