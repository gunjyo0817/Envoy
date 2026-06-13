from app.services import match_seeded_listing


def test_matches_seed_on_keywords():
    listing = match_seeded_listing("iPhone 14 128GB Midnight")
    assert listing is not None
    assert listing["listing_id"] == "demo-seed-001"


def test_no_match_returns_none():
    assert match_seeded_listing("Sony A7 III camera") is None
