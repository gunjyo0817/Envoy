import os, tempfile, importlib


def _fresh_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["ENVOY_DB"] = path
    import app.store as store
    importlib.reload(store)
    store.init_store()
    return store


def test_deal_roundtrips_negotiation_thread():
    store = _fresh_store()
    thread = [
        {"role": "buyer", "text": "€170?", "act": "initial_offer", "price": 170.0, "ts": "t1"},
        {"role": "seller", "text": "OK", "act": "accept", "price": 170.0, "ts": "t2"},
    ]
    store.record_deal({
        "session_id": "s-1", "user_id": 5, "query": "iPhone 14",
        "final_price": 170.0, "status": "done", "negotiation_thread": thread,
    })
    deal = store.get_deal("s-1")
    assert deal["negotiation_thread"] == thread
    assert deal["negotiation_thread"][1]["act"] == "accept"


def test_deal_without_thread_defaults_to_empty_list():
    store = _fresh_store()
    store.record_deal({"session_id": "s-2", "user_id": 5, "status": "failed"})
    assert store.get_deal("s-2")["negotiation_thread"] == []
