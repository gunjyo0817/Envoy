import os, json
from concurrent.futures import ThreadPoolExecutor
from tavily import TavilyClient
import google.generativeai as genai
from app.state import ProcurementState
from app.services import match_seeded_listing

def _build_queries(state: ProcurementState) -> list[str]:
    q = state["query"]
    loc = state["location"]
    return [
        f"{q} {loc} site:kleinanzeigen.de",
        f"{q} {loc} site:vinted.de",
    ]


def _gemini_generate_listings(query: str, location: str, budget_min: float, budget_max: float, n: int = 5) -> list[dict]:
    """Generate n realistic second-hand marketplace listings for the query (Gemini)."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        f"Generate {n} realistic used-marketplace listings for '{query}' near {location}. "
        f"Spread prices roughly between €{int(budget_min)} and €{int(budget_max)}. "
        f"Return JSON only (no markdown), a list of objects with keys: "
        f'"title" (str), "price_text" (e.g. "€185"), "location" (a {location} district), '
        f'"raw_description" (one German sentence incl. condition), '
        f'"seller_rating" (float 3.5-5.0), "seller_reviews" (int 1-80). '
        f"Vary brand/model realistically for the query."
    )
    text = model.generate_content(prompt).text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    items = json.loads(text)
    out = []
    for it in items[:n]:
        out.append({
            "platform": "kleinanzeigen",
            "title": it.get("title", query),
            "price_text": it.get("price_text", ""),
            "location": it.get("location", location),
            "url": "https://www.kleinanzeigen.de/s-anzeige/generated",
            "seller_rating": it.get("seller_rating"),
            "seller_reviews": it.get("seller_reviews"),
            "raw_description": it.get("raw_description", it.get("title", query)),
        })
    return out


def _deterministic_listings(query: str, location: str, budget_min: float, budget_max: float, n: int = 4) -> list[dict]:
    """Query-relevant listings without any LLM, so search never falls back to a wrong category."""
    lo = budget_min if budget_min > 0 else max(budget_max * 0.5, 1)
    listings = []
    for i in range(n):
        frac = i / max(n - 1, 1)
        price = round(lo + (budget_max - lo) * frac)
        listings.append({
            "platform": "kleinanzeigen",
            "title": f"{query} — Angebot {i + 1}",
            "price_text": f"€{price}",
            "location": location,
            "url": f"https://www.kleinanzeigen.de/s-anzeige/gen-{i}",
            "seller_rating": round(4.0 + 0.2 * (i % 5), 1),
            "seller_reviews": 5 + i * 7,
            "raw_description": f"{query}, guter Zustand. Standort {location}.",
        })
    return listings


def _fallback_listings(state) -> list[dict]:
    """Query-aware listings used when real search (Tavily) is unavailable."""
    query, loc = state["query"], state["location"]
    bmin, bmax = state["budget_min"], state["budget_max"]
    try:
        gen = _gemini_generate_listings(query, loc, bmin, bmax)
        if gen:
            return gen
    except Exception:
        pass
    return _deterministic_listings(query, loc, bmin, bmax)


def search_node(state: ProcurementState) -> dict:
    listings: list[dict] = []
    degraded = list(state.get("degraded", []))

    try:
        client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))

        def _run(query: str) -> list[dict]:
            resp = client.search(query=query, max_results=8, search_depth="advanced")
            return [{
                "platform": "kleinanzeigen" if "kleinanzeigen" in query else "vinted",
                "title": r.get("title", ""),
                "raw_description": r.get("content", ""),
                "url": r.get("url", ""),
                "price_text": "",
                "location": state["location"],
                "seller_rating": None,
                "seller_reviews": None,
            } for r in resp.get("results", [])]

        queries = _build_queries(state)
        # The two marketplace queries are independent — run them concurrently.
        with ThreadPoolExecutor(max_workers=len(queries)) as pool:
            for batch in pool.map(_run, queries):
                listings.extend(batch)
    except Exception:
        listings = []

    if not listings:
        degraded.append("search_generated_listings")
        listings = _fallback_listings(state)

    seed = match_seeded_listing(state["query"])
    if seed and not any(l.get("title") == seed.get("title") for l in listings):
        listings.insert(0, dict(seed))

    return {"raw_listings": listings, "degraded": degraded, "status": "reviewing"}
