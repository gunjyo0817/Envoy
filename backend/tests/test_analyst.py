from app.agents.analyst import score_listing, rank_candidates

def test_score_listing_prefers_lower_price():
    cheap = {"price_eur": 150.0, "condition": "very_good", "seller_rating": 4.5,
             "seller_reviews": 10, "distance_km": 3.0}
    expensive = {"price_eur": 200.0, "condition": "very_good", "seller_rating": 4.5,
                 "seller_reviews": 10, "distance_km": 3.0}
    assert score_listing(cheap, 0.0, 200.0) > score_listing(expensive, 0.0, 200.0)

def test_score_listing_penalises_poor_condition():
    good = {"price_eur": 175.0, "condition": "very_good", "seller_rating": 4.5,
            "seller_reviews": 10, "distance_km": 3.0}
    bad = {"price_eur": 175.0, "condition": "acceptable", "seller_rating": 4.5,
           "seller_reviews": 10, "distance_km": 3.0}
    assert score_listing(good, 0.0, 200.0) > score_listing(bad, 0.0, 200.0)

def test_rank_candidates_returns_sorted_list():
    listings = [
        {"price_eur": 200.0, "condition": "good", "seller_rating": 4.0,
         "seller_reviews": 5, "distance_km": 2.0},
        {"price_eur": 160.0, "condition": "very_good", "seller_rating": 4.8,
         "seller_reviews": 20, "distance_km": 5.0},
    ]
    ranked = rank_candidates(listings, 0.0, 200.0)
    assert ranked[0]["price_eur"] == 160.0   # better deal should rank first
    assert all("score" in r for r in ranked)

def test_rank_candidates_filters_are_caller_responsibility_but_scoring_uses_range():
    # within a tight range, a listing near the min scores higher than near the max
    near_min = {"price_eur": 110.0, "condition": "good", "seller_rating": 4.0, "seller_reviews": 5, "distance_km": 2.0}
    near_max = {"price_eur": 190.0, "condition": "good", "seller_rating": 4.0, "seller_reviews": 5, "distance_km": 2.0}
    assert score_listing(near_min, 100.0, 200.0) > score_listing(near_max, 100.0, 200.0)
