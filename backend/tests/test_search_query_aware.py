from unittest.mock import patch
from app.agents.search import search_node, _fallback_listings


def _state(query="Sony A7 III camera"):
    return {"query": query, "location": "München", "budget_min": 0.0, "budget_max": 900.0, "degraded": []}


def test_fallback_is_query_relevant_not_iphone():
    with patch("app.agents.search._gemini_generate_listings", side_effect=Exception("no gemini")):
        listings = _fallback_listings(_state())
    assert listings, "fallback must produce listings"
    assert all("iphone" not in (l.get("title", "").lower()) for l in listings)
    assert any("sony" in (l.get("title", "").lower()) for l in listings)
    assert all(l.get("price_text") for l in listings)


def test_search_node_injects_seeded_listing_when_query_matches():
    seed = {"platform": "kleinanzeigen", "title": "iPhone 14 128GB Midnight", "price_text": "€185",
            "location": "Schwabing, München", "url": "u", "raw_description": "x",
            "seller_rating": 4.9, "seller_reviews": 24, "listing_id": "demo-seed-001"}
    with patch("app.agents.search._gemini_generate_listings", return_value=[
                   {"platform": "kleinanzeigen", "title": "iPhone 14 128GB", "price_text": "€190",
                    "location": "München", "url": "u2", "raw_description": "y",
                    "seller_rating": 4.5, "seller_reviews": 10}]), \
         patch("app.agents.search.match_seeded_listing", return_value=seed):
        out = search_node(_state(query="iPhone 14 128GB"))
    titles = [l["title"] for l in out["raw_listings"]]
    assert "iPhone 14 128GB Midnight" in titles
    assert out["status"] == "reviewing"


def test_search_node_no_seed_when_query_differs():
    with patch("app.agents.search._gemini_generate_listings", return_value=[
                   {"platform": "kleinanzeigen", "title": "Sony A7 III", "price_text": "€750",
                    "location": "München", "url": "u", "raw_description": "z",
                    "seller_rating": 4.6, "seller_reviews": 8}]), \
         patch("app.agents.search.match_seeded_listing", return_value=None):
        out = search_node(_state(query="Sony A7 III camera"))
    assert any("sony" in l["title"].lower() for l in out["raw_listings"])
    assert all("iphone" not in l["title"].lower() for l in out["raw_listings"])
