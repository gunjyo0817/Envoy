"""
GLiNER2 (via Pioneer) vs Gemini: accuracy / latency / cost comparison.
Run: cd backend && python ../eval/gliner_vs_gemini.py
"""
import os, re, json, time, statistics
from dotenv import load_dotenv; load_dotenv()
import httpx
import google.generativeai as genai

_PIONEER_URL = "https://api.pioneer.ai/inference"
_BASE_MODEL = "fastino/gliner2-base-v1"

SAMPLES = [
    {
        "text": "iPhone 14 128GB Space Grey. Sehr guter Zustand, keine Kratzer. €175. München Schwabing.",
        "expected": {"brand": "Apple", "model": "iPhone 14 128GB Space Grey",
                     "condition": "very_good", "price_eur": 175.0, "location_city": "München"}
    },
    {
        "text": "Sony A7 III Kamera mit 28-70mm Objektiv. Guter Zustand. €890 VHB. Berlin Mitte.",
        "expected": {"brand": "Sony", "model": "A7 III",
                     "condition": "good", "price_eur": 890.0, "location_city": "Berlin"}
    },
    {
        "text": "MacBook Air M2 256GB Space Gray - wie neu, 6 Monate alt, €950.",
        "expected": {"brand": "Apple", "model": "MacBook Air M2 256GB",
                     "condition": "like_new", "price_eur": 950.0, "location_city": None}
    },
]

_CONDITION_MAP = {
    "brandneu": "new", "neu": "new", "new": "new",
    "wie neu": "like_new", "wie-neu": "like_new",
    "sehr gut": "very_good", "very good": "very_good",
    "gut": "good", "guter": "good", "good": "good",
    "akzeptabel": "acceptable", "acceptable": "acceptable",
}

def _normalize_condition(text: str) -> str:
    lower = text.lower()
    for key, val in _CONDITION_MAP.items():
        if key in lower:
            return val
    return "good"

def _parse_price(text: str) -> float | None:
    nums = re.findall(r'\d+(?:[.,]\d+)?', text.replace(".", "").replace(",", "."))
    try:
        return float(nums[0]) if nums else None
    except ValueError:
        return None

def _entities_to_dict(entities: list) -> dict:
    result: dict = {"brand": None, "model": None, "condition": None,
                    "price_eur": None, "location_city": None, "defects": []}
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
    return result

def _call_pioneer(text: str) -> tuple[dict, float]:
    api_key = os.environ["PIONEER_API_KEY"]
    model_id = os.environ.get("PIONEER_MODEL_ID", _BASE_MODEL)
    t0 = time.perf_counter()
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
    elapsed = time.perf_counter() - t0
    resp.raise_for_status()
    return _entities_to_dict(resp.json().get("entities", [])), elapsed

def _call_gemini(text: str) -> tuple[dict, float]:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        'Extract from this second-hand listing. Return JSON only, no markdown:\n'
        '{"brand": str, "model": str, "condition": "new"|"like_new"|"very_good"|"good"|"acceptable",'
        ' "price_eur": float|null, "location_city": str|null, "defects": [str]}\n'
        f'Listing: {text}'
    )
    t0 = time.perf_counter()
    result = model.generate_content(prompt)
    elapsed = time.perf_counter() - t0
    raw = result.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(raw), elapsed

def _score(predicted: dict, expected: dict) -> float:
    fields = ["brand", "model", "condition", "price_eur", "location_city"]
    correct = sum(
        1 for f in fields
        if str(predicted.get(f, "")).lower() == str(expected.get(f, "")).lower()
    )
    return correct / len(fields)

def run():
    pioneer_scores, pioneer_latencies = [], []
    gemini_scores, gemini_latencies = [], []

    for s in SAMPLES:
        print(f"\nSample: {s['text'][:60]}...")
        try:
            p_out, p_lat = _call_pioneer(s["text"])
            score = _score(p_out, s["expected"])
            pioneer_scores.append(score)
            pioneer_latencies.append(p_lat)
            print(f"  Pioneer: {p_out}  score={score:.0%}  {p_lat*1000:.0f}ms")
        except Exception as e:
            print(f"  Pioneer error: {e}")
            pioneer_scores.append(0.0)
            pioneer_latencies.append(999.0)

        try:
            g_out, g_lat = _call_gemini(s["text"])
            score = _score(g_out, s["expected"])
            gemini_scores.append(score)
            gemini_latencies.append(g_lat)
            print(f"  Gemini:  {g_out}  score={score:.0%}  {g_lat*1000:.0f}ms")
        except Exception as e:
            print(f"  Gemini error: {e}")
            gemini_scores.append(0.0)
            gemini_latencies.append(999.0)

    print("\n=== GLiNER2 (Pioneer) vs Gemini Flash — Extraction Benchmark ===\n")
    print(f"{'Metric':<25} {'GLiNER2/Pioneer':>18} {'Gemini Flash':>14}")
    print("-" * 60)
    print(f"{'Accuracy (avg)':<25} {statistics.mean(pioneer_scores)*100:>17.1f}% {statistics.mean(gemini_scores)*100:>13.1f}%")
    print(f"{'Latency p50 (ms)':<25} {statistics.median(pioneer_latencies)*1000:>17.0f}  {statistics.median(gemini_latencies)*1000:>13.0f}")
    print(f"{'Latency p95 (ms)':<25} {max(pioneer_latencies)*1000:>17.0f}  {max(gemini_latencies)*1000:>13.0f}")
    print(f"{'Cost per call (est.)':<25} {'~$0.00003':>18} {'~$0.003':>14}")
    print()

if __name__ == "__main__":
    run()
