import pytest
from unittest.mock import patch, MagicMock
from app.agents.search import search_node
from app.state import initial_state

def test_search_node_uses_mock_fallback_when_tavily_raises():
    state = initial_state("iPhone 14", 0.0, 200.0, "good+", "München", 15)

    with patch("app.agents.search.TavilyClient") as MockClient:
        MockClient.return_value.search.side_effect = Exception("quota exceeded")
        result = search_node(state)

    assert len(result["raw_listings"]) > 0
    assert "tavily_fallback_to_mock" in result["degraded"]
    assert result["status"] == "reviewing"

def test_search_node_returns_listings_on_success():
    state = initial_state("iPhone 14", 0.0, 200.0, "good+", "München", 15)
    fake_results = {"results": [{"title": "iPhone 14", "content": "€180 München", "url": "https://kleinanzeigen.de/1"}]}

    with patch("app.agents.search.TavilyClient") as MockClient:
        MockClient.return_value.search.return_value = fake_results
        result = search_node(state)

    assert len(result["raw_listings"]) > 0
    assert "tavily_fallback_to_mock" not in result["degraded"]
    assert result["status"] == "reviewing"
