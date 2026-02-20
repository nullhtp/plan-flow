"""Unit tests for AI web search tool with mocked Perplexity (ChatOpenAI)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.ai.tools.web_search import make_web_search


@pytest.mark.asyncio
@patch("app.domains.ai.tools.web_search.settings")
async def test_web_search_excluded_without_api_key(mock_settings: MagicMock) -> None:
    """Web search tool returns None when no Perplexity API key configured."""
    mock_settings.perplexity_api_key = ""

    tool = make_web_search()
    assert tool is None


@pytest.mark.asyncio
@patch("app.domains.ai.tools.web_search._get_perplexity_llm")
@patch("app.domains.ai.tools.web_search.settings")
async def test_web_search_returns_results(
    mock_settings: MagicMock,
    mock_get_llm: MagicMock,
) -> None:
    """Web search tool returns synthesized answer from Perplexity."""
    mock_settings.perplexity_api_key = "pplx-test-key"

    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.content = "Here is information about the topic."
    mock_response.response_metadata = {
        "citations": ["https://example.com/1", "https://example.com/2"]
    }

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_get_llm.return_value = mock_llm

    tool = make_web_search()
    assert tool is not None

    result = await tool.ainvoke({"query": "test query"})

    assert isinstance(result, dict)
    assert result["status"] == "executed"
    assert "answer" in result
    assert result["answer"] == "Here is information about the topic."
    assert result["citations"] == ["https://example.com/1", "https://example.com/2"]
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("app.domains.ai.tools.web_search._get_perplexity_llm")
@patch("app.domains.ai.tools.web_search.settings")
async def test_web_search_handles_error(
    mock_settings: MagicMock,
    mock_get_llm: MagicMock,
) -> None:
    """Web search tool handles Perplexity errors gracefully."""
    mock_settings.perplexity_api_key = "pplx-test-key"

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("API error"))
    mock_get_llm.return_value = mock_llm

    tool = make_web_search()
    assert tool is not None

    result = await tool.ainvoke({"query": "test query"})

    assert isinstance(result, dict)
    assert result["status"] == "failed"
    assert "error" in result


@pytest.mark.asyncio
@patch("app.domains.ai.tools.web_search._get_perplexity_llm")
@patch("app.domains.ai.tools.web_search.settings")
async def test_web_search_no_citations(
    mock_settings: MagicMock,
    mock_get_llm: MagicMock,
) -> None:
    """Web search works when response has no citations metadata."""
    mock_settings.perplexity_api_key = "pplx-test-key"

    mock_response = MagicMock()
    mock_response.content = "Answer without citations."
    mock_response.response_metadata = {}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    mock_get_llm.return_value = mock_llm

    tool = make_web_search()
    assert tool is not None

    result = await tool.ainvoke({"query": "test query"})

    assert isinstance(result, dict)
    assert result["status"] == "executed"
    assert result["citations"] == []
