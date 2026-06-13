"""
GLiNER2 (via Pioneer) vs Gemini: accuracy / latency / cost comparison.
Run: python eval/gliner_vs_gemini.py
"""
import os, json, time, statistics
from dotenv import load_dotenv; load_dotenv()
import httpx
import google.generativeai as genai

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

LISTING_PROMPT_TEMPLATE = """Extract from this second-hand listing. Return JSON only, no markdown:
{{"brand": str, "model": str, "condition": "new"|"like_new"|"very_good"|"good"|"acceptable",
 "price_eur": float|null, "location_city": str|null, "defects": [str]}}
Listing: {text}"""

def _call_pioneer(text: str) -> tuple[dict, float]:
    endpoint = os.environ["PIONEER_ENDPOINT"]
    prompt = LISTING_PROMPT_TEMPLATE.format(text=text)
    t0 = time.perf_counter()
    resp = httpx.post(endpoint, json={"prompt": prompt}, timeout=10.0)
    elapsed = time.perf_counter() - t0
    return resp.json(), elapsed

def _call_gemini(text: str) -> tuple[dict, float]:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = LISTING_PROMPT_TEMPLATE.format(text=text)
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
        try:
            p_out, p_lat = _call_pioneer(s["text"])
            pioneer_scores.append(_score(p_out, s["expected"]))
            pioneer_latencies.append(p_lat)
        except Exception as e:
            print(f"Pioneer error: {e}")
            pioneer_scores.append(0.0)
            pioneer_latencies.append(999.0)

        try:
            g_out, g_lat = _call_gemini(s["text"])
            gemini_scores.append(_score(g_out, s["expected"]))
            gemini_latencies.append(g_lat)
        except Exception as e:
            print(f"Gemini error: {e}")
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
