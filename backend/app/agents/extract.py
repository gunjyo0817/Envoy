import os, json, httpx, datetime
import google.generativeai as genai
from app.state import ProcurementState

_LISTING_SCHEMA = """Extract from this second-hand listing. Return JSON only, no markdown:
{"brand": str, "model": str, "condition": "new"|"like_new"|"very_good"|"good"|"acceptable",
 "price_eur": float|null, "location_city": str, "defects": [str]}
Listing: """

_MSG_SCHEMA = """Classify this negotiation message. Return JSON only:
{"act": "initial_offer"|"counter_offer"|"accept"|"reject"|"question"|"stall", "price": float|null}
Message: """

def _call_pioneer(prompt: str) -> dict:
    endpoint = os.environ["PIONEER_ENDPOINT"]
    resp = httpx.post(endpoint, json={"prompt": prompt}, timeout=5.0)
    resp.raise_for_status()
    return resp.json()

def _call_gemini_extract(prompt: str) -> dict:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.0-flash")
    result = model.generate_content(prompt)
    text = result.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)

def extract_listing(raw_text: str, record_degraded: list | None = None) -> dict:
    prompt = _LISTING_SCHEMA + raw_text
    try:
        return _call_pioneer(prompt)
    except Exception:
        if record_degraded is not None:
            record_degraded.append("gliner2_fallback_to_gemini")
        return _call_gemini_extract(prompt)

def classify_message(text: str, record_degraded: list | None = None) -> dict:
    prompt = _MSG_SCHEMA + text
    try:
        return _call_pioneer(prompt)
    except Exception:
        if record_degraded is not None:
            record_degraded.append("gliner2_fallback_to_gemini")
        return _call_gemini_extract(prompt)

def extract_node(state: ProcurementState) -> dict:
    degraded = list(state.get("degraded", []))
    structured = []
    for listing in state["raw_listings"]:
        raw = f"{listing.get('title', '')} {listing.get('raw_description', '')} {listing.get('price_text', '')}"
        extracted = extract_listing(raw, record_degraded=degraded)
        structured.append({**listing, **extracted})
    return {
        "structured_listings": structured,
        "degraded": list(set(degraded)),
    }
