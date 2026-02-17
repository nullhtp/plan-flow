"""Unit tests for AI web search tool with mocked Tavily client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.domains.ai.tools.web_search import make_web_search


@pytest.mark.asyncio
@patch("app.domains.ai.tools.web_search.settings")
async def test_web_search_excluded_without_api_key(mock_settings: MagicMock) -> None:
    """Web search tool returns None when no API key configured."""
    mock_settings.tavily_api_key = None

    tool = make_web_search()
    assert tool is None


@pytest.mark.asyncio
@patch("app.domains.ai.tools.web_search.settings")
@patch("app.domains.ai.tools.web_search.TavilyClient")
async def test_web_search_returns_results(
    mock_tavily_cls: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Web search tool returns formatted results from Tavily."""
    mock_settings.tavily_api_key = "tvly-test-key"
    mock_settings.ai_web_search_max_results = 3

    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "content": "Some content here",
                "score": 0.95,
            }
        ]
    }
    mock_tavily_cls.return_value = mock_client

    tool = make_web_search()
    assert tool is not None

    result = await tool.ainvoke({"query": "test query"})

    assert isinstance(result, (str, dict, list))
    # The tool should have called Tavily
    mock_client.search.assert_called_once()


@pytest.mark.asyncio
@patch("app.domains.ai.tools.web_search.settings")
@patch("app.domains.ai.tools.web_search.TavilyClient")
async def test_web_search_handles_error(
    mock_tavily_cls: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Web search tool handles Tavily errors gracefully."""
    mock_settings.tavily_api_key = "tvly-test-key"
    mock_settings.ai_web_search_max_results = 3

    mock_client = MagicMock()
    mock_client.search.side_effect = Exception("API error")
    mock_tavily_cls.return_value = mock_client

    tool = make_web_search()
    assert tool is not None

    result = await tool.ainvoke({"query": "test query"})

    # Should return an error dict/string rather than raising
    if isinstance(result, dict):
        assert "error" in result or "status" in result
    elif isinstance(result, str):
        assert "error" in result.lower() or "failed" in result.lower()
