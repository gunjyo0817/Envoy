from app.agents.analyst import score_listing, rank_candidates

def test_score_listing_prefers_lower_price():
    cheap = {"price_eur": 150.0, "condition": "very_good", "seller_rating": 4.5,
             "seller_reviews": 10, "distance_km": 3.0}
    expensive = {"price_eur": 200.0, "condition": "very_good", "seller_rating": 4.5,
                 "seller_reviews": 10, "distance_km": 3.0}
    assert score_listing(cheap, budget=200.0) > score_listing(expensive, budget=200.0)

def test_score_listing_penalises_poor_condition():
    good = {"price_eur": 175.0, "condition": "very_good", "seller_rating": 4.5,
            "seller_reviews": 10, "distance_km": 3.0}
    bad = {"price_eur": 175.0, "condition": "acceptable", "seller_rating": 4.5,
           "seller_reviews": 10, "distance_km": 3.0}
    assert score_listing(good, budget=200.0) > score_listing(bad, budget=200.0)

def test_rank_candidates_returns_sorted_list():
    listings = [
        {"price_eur": 200.0, "condition": "good", "seller_rating": 4.0,
         "seller_reviews": 5, "distance_km": 2.0},
        {"price_eur": 160.0, "condition": "very_good", "seller_rating": 4.8,
         "seller_reviews": 20, "distance_km": 5.0},
    ]
    ranked = rank_candidates(listings, budget=200.0)
    assert ranked[0]["price_eur"] == 160.0   # better deal should rank first
    assert all("score" in r for r in ranked)
