"""Web search tool using Tavily Search API.

Optional — only registered when TAVILY_API_KEY is configured.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)


def make_web_search() -> Any | None:
    """Create a web_search tool. Returns None if Tavily is not configured."""
    if not settings.tavily_api_key:
        return None

    @tool
    async def web_search(query: str, max_results: int = 0) -> dict[str, Any]:
        """Search the web for information to help with a task.

        Use when the user asks for research or when external
        information is needed.

        Args:
            query: The search query.
            max_results: Maximum number of results (0 = use default).
        """
        try:
            from tavily import (
                AsyncTavilyClient,  # pyright: ignore[reportMissingTypeStubs, reportUnknownVariableType]
            )

            client = AsyncTavilyClient(api_key=settings.tavily_api_key)  # pyright: ignore[reportUnknownMemberType]
            limit = (
                max_results if max_results > 0 else settings.ai_web_search_max_results
            )

            response = await client.search(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                query=query,
                max_results=limit,
            )

            results = []
            for item in response.get("results", []):  # pyright: ignore[reportUnknownMemberType]
                results.append(  # pyright: ignore[reportUnknownMemberType]
                    {
                        "title": item.get("title", ""),  # pyright: ignore[reportUnknownMemberType]
                        "url": item.get("url", ""),  # pyright: ignore[reportUnknownMemberType]
                        "content": item.get("content", ""),  # pyright: ignore[reportUnknownMemberType]
                        "score": item.get("score", 0),  # pyright: ignore[reportUnknownMemberType]
                    }
                )

            return {"status": "executed", "results": results, "query": query}
        except Exception:
            logger.exception("Web search failed")
            return {
                "status": "failed",
                "error": "Web search is temporarily unavailable",
            }

    return web_search
