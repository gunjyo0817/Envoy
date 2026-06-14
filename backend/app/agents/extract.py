import os, re, json, httpx, datetime
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from app.state import ProcurementState

# Analyst only keeps the top 5 after budget-filtering, so extracting every raw
# listing is wasted latency. Cap how many we run through the (per-listing) LLM.
_MAX_EXTRACT = int(os.environ.get("ENVOY_MAX_EXTRACT", "8"))

_PIONEER_URL = "https://api.pioneer.ai/inference"
_BASE_MODEL = "fastino/gliner2-base-v1"

# Condition keyword → canonical enum value (German + English)
_CONDITION_MAP = {
    "brandneu": "new", "neu": "new", "new": "new",
    "wie neu": "like_new", "wie-neu": "like_new", "like new": "like_new",
    "sehr gut": "very_good", "very good": "very_good", "sehr guter": "very_good",
    "gut": "good", "guter": "good", "good": "good",
    "akzeptabel": "acceptable", "acceptable": "acceptable", "ok": "acceptable",
}

def _normalize_condition(text: str) -> str:
    lower = text.lower().strip()
    for key, val in _CONDITION_MAP.items():
        if key in lower:
            return val
    return "good"

def _parse_price(text: str) -> float | None:
    # Prefer the price the speaker is *proposing*: the number after the last
    # German "für" ("for"), else the last number in the message. This avoids
    # grabbing an echoed earlier price, e.g. "€165 ist wenig, ich mache €179"
    # should read 179, not 165.
    cleaned = text.replace(".", "").replace(",", ".")
    fuer = re.findall(r'für\s*€?\s*(\d+(?:\.\d+)?)', cleaned, flags=re.IGNORECASE)
    nums = fuer if fuer else re.findall(r'\d+(?:\.\d+)?', cleaned)
    if nums:
        try:
            return float(nums[-1])
        except ValueError:
            pass
    return None

def _entities_to_listing(entities: list) -> dict:
    result: dict = {
        "brand": None, "model": None, "condition": None,
        "price_eur": None, "location_city": None, "defects": [],
    }
    for ent in sorted(entities, key=lambda e: e.get("score", 0), reverse=True):
        label, text = ent.get("label"), ent.get("text", "")
        if label == "brand" and not result["brand"]:
            result["brand"] = text
        elif label == "model" and not result["model"]:
            result["model"] = text
        elif label == "condition" and not result["condition"]:
            result["condition"] = _normalize_condition(text)
        elif label == "price_eur" and result["price_eur"] is None:
            result["price_eur"] = _parse_price(text)
        elif label == "location_city" and not result["location_city"]:
            result["location_city"] = text
        elif label == "defect":
            result["defects"].append(text)
    if not result["condition"]:
        result["condition"] = "good"
    return result

def _pioneer_listing(text: str) -> dict:
    api_key = os.environ["PIONEER_API_KEY"]
    model_id = os.environ.get("PIONEER_MODEL_ID", _BASE_MODEL)
    resp = httpx.post(
        _PIONEER_URL,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={
            "model_id": model_id,
            "text": text,
            "schema": {
                "entities": ["brand", "model", "condition", "price_eur", "location_city", "defect"]
            },
            "threshold": 0.3,
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    return _entities_to_listing(resp.json().get("entities", []))

def _pioneer_classify(text: str) -> dict:
    api_key = os.environ["PIONEER_API_KEY"]
    model_id = os.environ.get("PIONEER_MODEL_ID", _BASE_MODEL)
    resp = httpx.post(
        _PIONEER_URL,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={
            "model_id": model_id,
            "text": text,
            "schema": {
                "classifications": [{
                    "task": "negotiation_act",
                    "labels": ["initial_offer", "counter_offer", "accept", "reject", "question", "stall"],
                }]
            },
            "threshold": 0.3,
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    act = "stall"
    for c in resp.json().get("classifications", []):
        if c.get("task") == "negotiation_act":
            act = c.get("label", "stall")
    price = _parse_price(text)
    return {"act": act, "price": price}

def _gemini_extract_listing(raw_text: str) -> dict:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        'Extract from this second-hand listing. Return JSON only, no markdown:\n'
        '{"brand": str, "model": str, "condition": "new"|"like_new"|"very_good"|"good"|"acceptable",'
        ' "price_eur": float|null, "location_city": str|null, "defects": [str]}\n'
        f'Listing: {raw_text}'
    )
    result = model.generate_content(prompt)
    text = result.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def _gemini_classify(text: str) -> dict:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        'Classify this negotiation message. Return JSON only:\n'
        '{"act": "initial_offer"|"counter_offer"|"accept"|"reject"|"question"|"stall", "price": float|null}\n'
        f'Message: {text}'
    )
    result = model.generate_content(prompt)
    raw = result.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(raw)

def extract_listing(raw_text: str, record_degraded: list | None = None) -> dict:
    try:
        return _pioneer_listing(raw_text)
    except Exception:
        if record_degraded is not None:
            record_degraded.append("gliner2_fallback_to_gemini")
        return _gemini_extract_listing(raw_text)

def classify_message(text: str, record_degraded: list | None = None) -> dict:
    try:
        return _pioneer_classify(text)
    except Exception:
        if record_degraded is not None:
            record_degraded.append("gliner2_fallback_to_gemini")
        return _gemini_classify(text)

def _backfill(extracted: dict, listing: dict) -> dict:
    """The base GLiNER2 model often misses price/location. Fall back to the
    listing's own structured fields (price_text, location) so downstream
    scoring and display always have real values."""
    if not extracted.get("price_eur"):
        extracted["price_eur"] = _parse_price(listing.get("price_text", ""))
    if not extracted.get("location_city"):
        extracted["location_city"] = listing.get("location")
    if not extracted.get("model"):
        extracted["model"] = listing.get("title")
    return extracted

def _extract_one(listing: dict, degraded: list) -> dict:
    raw = f"{listing.get('title', '')} {listing.get('raw_description', '')} {listing.get('price_text', '')}"
    extracted = _backfill(extract_listing(raw, record_degraded=degraded), listing)
    return {**listing, **extracted}


def extract_node(state: ProcurementState) -> dict:
    degraded = list(state.get("degraded", []))
    listings = state["raw_listings"][:_MAX_EXTRACT]
    # Each extraction is an independent network call; run them concurrently so
    # total latency is ~one call instead of the sum of all of them.
    if listings:
        with ThreadPoolExecutor(max_workers=len(listings)) as pool:
            structured = list(pool.map(lambda l: _extract_one(l, degraded), listings))
    else:
        structured = []
    return {
        "structured_listings": structured,
        "degraded": list(set(degraded)),
    }
