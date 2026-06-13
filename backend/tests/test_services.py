import base64
from unittest.mock import patch
from fastapi.testclient import TestClient


def _client():
    from app.main import app
    return TestClient(app)


def test_translate_returns_translation():
    with patch("app.main.translate", return_value="Hello, that is too little.") as m:
        r = _client().post("/translate", json={"text": "Hallo, das ist zu wenig.", "target_lang": "en"})
    assert r.status_code == 200
    assert r.json() == {"translation": "Hello, that is too little."}
    m.assert_called_once_with("Hallo, das ist zu wenig.", "en")


def test_vision_identify_returns_query():
    img_b64 = base64.b64encode(b"fake-image-bytes").decode()
    with patch("app.main.identify_product", return_value="iPhone 14 128GB") as m:
        r = _client().post("/vision/identify", json={"image_base64": img_b64})
    assert r.status_code == 200
    assert r.json() == {"query": "iPhone 14 128GB"}
    m.assert_called_once_with(img_b64)


def test_vision_identify_rejects_bad_base64():
    with patch("app.main.identify_product", side_effect=ValueError("Invalid base64 image data")):
        r = _client().post("/vision/identify", json={"image_base64": "%%%not-base64%%%"})
    assert r.status_code == 400


def test_reverse_geocode_returns_location_text():
    with patch("app.main.reverse_geocode", return_value="München") as m:
        r = _client().get("/geocode/reverse", params={"lat": 48.137, "lng": 11.575})
    assert r.status_code == 200
    assert r.json() == {"location": "München"}
    m.assert_called_once_with(48.137, 11.575)
