import os, tempfile, importlib


def _fresh_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["ENVOY_DB"] = path
    import app.store as store
    importlib.reload(store)
    store.init_store()
    return store, path


def test_telegram_link_roundtrip():
    store, _ = _fresh_store()
    store.register_chat(chat_id=111, role="seller")
    store.attach_session(chat_id=111, session_id="s-1")
    link = store.resolve_chat(111)
    assert link["role"] == "seller" and link["session_id"] == "s-1"
    assert store.chat_for_role("seller") == 111


def test_record_and_list_deals():
    store, _ = _fresh_store()
    store.record_deal({
        "session_id": "s-2", "user_id": 7, "query": "iPhone 14",
        "thumbnail": "http://img", "final_price": 180.0,
        "seller_label": "Kleinanzeigen", "meetup": {"location": "Marienplatz"},
        "status": "done",
    })
    deals = store.list_deals(user_id=7)
    assert len(deals) == 1 and deals[0]["final_price"] == 180.0
    assert deals[0]["meetup"]["location"] == "Marienplatz"
    assert store.get_deal("s-2")["status"] == "done"
