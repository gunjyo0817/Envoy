from unittest.mock import patch
from app.agents.extract import extract_listing, classify_message

def test_extract_listing_returns_required_fields():
    sample = "iPhone 14 128GB Space Grey. Sehr guter Zustand. €175. München Schwabing."
    with patch("app.agents.extract._pioneer_listing") as mock_pioneer:
        mock_pioneer.return_value = {
            "brand": "Apple", "model": "iPhone 14 128GB Space Grey",
            "condition": "very_good", "price_eur": 175.0,
            "location_city": "München", "defects": []
        }
        result = extract_listing(sample)

    assert result["price_eur"] == 175.0
    assert result["condition"] == "very_good"
    assert "brand" in result

def test_classify_message_returns_valid_act():
    with patch("app.agents.extract._pioneer_classify") as mock_pioneer:
        mock_pioneer.return_value = {"act": "counter_offer", "price": 160.0}
        result = classify_message("Ich mache es für €160.")

    assert result["act"] == "counter_offer"

def test_extract_listing_falls_back_to_gemini_on_pioneer_failure():
    sample = "iPhone 14 €175 München"
    with patch("app.agents.extract._pioneer_listing", side_effect=Exception("timeout")):
        with patch("app.agents.extract._gemini_extract_listing") as mock_gemini:
            mock_gemini.return_value = {
                "brand": "Apple", "model": "iPhone 14", "condition": "good",
                "price_eur": 175.0, "location_city": "München", "defects": []
            }
            result = extract_listing(sample, record_degraded=[])

    assert result["price_eur"] == 175.0
