"""Web search tool using Perplexity Sonar API.

Uses LangChain's ChatOpenAI with Perplexity's OpenAI-compatible endpoint.
Optional — only registered when PERPLEXITY_API_KEY is configured.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)

PERPLEXITY_BASE_URL = "https://api.perplexity.ai"


def _get_perplexity_llm() -> Any:
    """Create a ChatOpenAI instance configured for Perplexity Sonar."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.perplexity_model,
        api_key=settings.perplexity_api_key,  # pyright: ignore[reportArgumentType]
        base_url=PERPLEXITY_BASE_URL,
        timeout=30.0,
    )


def make_web_search() -> Any | None:
    """Create a web_search tool. Returns None if Perplexity is not configured."""
    if not settings.perplexity_api_key:
        return None

    @tool
    async def web_search(query: str) -> dict[str, Any]:
        """Search the web for current information using Perplexity.

        Use when the user asks for research or when external
        information is needed. Returns a synthesized answer
        with source citations.

        Args:
            query: The search query.
        """
        try:
            llm = _get_perplexity_llm()

            response = await llm.ainvoke(
                [{"role": "user", "content": query}],
            )

            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Extract citations if available in response metadata
            citations: list[str] = []
            if hasattr(response, "response_metadata"):
                citations = response.response_metadata.get("citations", [])

            return {
                "status": "executed",
                "answer": content,
                "citations": citations,
                "query": query,
            }
        except Exception:
            logger.exception("Web search failed")
            return {
                "status": "failed",
                "error": "Web search is temporarily unavailable",
            }

    return web_search
