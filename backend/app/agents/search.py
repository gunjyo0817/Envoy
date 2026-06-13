import os
from tavily import TavilyClient
from app.state import ProcurementState
from app.mock.listings import FACEBOOK_LISTINGS, VINTED_FALLBACK_LISTINGS

def _build_queries(state: ProcurementState) -> list[str]:
    q = state["query"]
    loc = state["location"]
    return [
        f"{q} {loc} site:kleinanzeigen.de",
        f"{q} {loc} site:vinted.de",
    ]

def search_node(state: ProcurementState) -> dict:
    listings: list[dict] = []
    degraded = list(state.get("degraded", []))

    try:
        client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
        for query in _build_queries(state):
            resp = client.search(query=query, max_results=10, search_depth="advanced")
            for r in resp.get("results", []):
                listings.append({
                    "platform": "kleinanzeigen" if "kleinanzeigen" in query else "vinted",
                    "title": r.get("title", ""),
                    "raw_description": r.get("content", ""),
                    "url": r.get("url", ""),
                    "price_text": "",   # GLiNER2 will extract
                    "location": state["location"],
                    "seller_rating": None,
                    "seller_reviews": None,
                })
    except Exception:
        degraded.append("tavily_fallback_to_mock")
        listings = FACEBOOK_LISTINGS + VINTED_FALLBACK_LISTINGS

    # Always add FB mock listings (unavailable via scraping)
    if "tavily_fallback_to_mock" not in degraded:
        listings += FACEBOOK_LISTINGS

    return {
        "raw_listings": listings,
        "degraded": degraded,
        "status": "reviewing",
    }
