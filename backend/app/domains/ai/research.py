"""Shared research utilities for the AI pipeline.

Provides reusable search and URL fetch functions that can be called
directly from pipeline nodes (not LangChain tools).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    content: str
    score: float = 0.0


@dataclass
class ResearchContext:
    """Compiled research results from web searches and URL extractions."""

    results: list[SearchResult] = field(default_factory=list)
    queries_used: int = 0
    budget_remaining: int = 0
    fetched_contents: dict[str, str] = field(default_factory=dict)
    """URL -> extracted full-page content."""


async def execute_search(
    query: str,
    max_results: int = 5,
) -> list[SearchResult]:
    """Execute a single web search via Tavily.

    Returns an empty list if Tavily is not configured or the search fails.
    This is a standalone utility — not a LangChain tool.
    """
    if not settings.tavily_api_key:
        return []

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(
            query=query,
            max_results=max_results,
        )

        results: list[SearchResult] = []
        for item in response.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                )
            )
        return results

    except Exception:
        logger.warning("Web search failed for query: %s", query, exc_info=True)
        return []


async def execute_searches_parallel(
    queries: list[str],
    max_results_per_query: int = 5,
) -> list[SearchResult]:
    """Execute multiple searches in parallel, deduplicate by URL.

    Returns a flat, deduplicated list of results sorted by score (desc).
    """
    if not queries:
        return []

    tasks = [
        asyncio.create_task(execute_search(q, max_results_per_query)) for q in queries
    ]
    all_results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls: set[str] = set()
    deduped: list[SearchResult] = []

    for result_or_error in all_results_lists:
        if isinstance(result_or_error, BaseException):
            logger.warning("Search task failed: %s", result_or_error)
            continue
        for r in result_or_error:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                deduped.append(r)

    # Sort by relevance score descending
    deduped.sort(key=lambda r: r.score, reverse=True)
    return deduped


async def fetch_top_urls(
    results: list[SearchResult],
    max_urls: int | None = None,
    max_chars: int = 4000,
    timeout: float = 10.0,
) -> dict[str, str]:
    """Fetch full content from the top N search result URLs.

    Returns a dict mapping URL -> extracted text content.
    Failures are silently skipped (logged at warning level).
    """
    from app.domains.ai.tools.url_fetch import fetch_url_content

    limit = max_urls if max_urls is not None else settings.ai_max_fetch_urls
    urls_to_fetch = [r.url for r in results[:limit]]

    if not urls_to_fetch:
        return {}

    tasks = [
        asyncio.create_task(fetch_url_content(url, max_chars, timeout))
        for url in urls_to_fetch
    ]
    contents = await asyncio.gather(*tasks, return_exceptions=True)

    fetched: dict[str, str] = {}
    for url, content_or_error in zip(urls_to_fetch, contents, strict=False):
        if isinstance(content_or_error, BaseException):
            logger.warning("URL fetch failed for %s: %s", url, content_or_error)
            continue
        if content_or_error is not None:
            fetched[url] = content_or_error

    return fetched


def is_research_available() -> bool:
    """Check if web research is available (Tavily configured)."""
    return bool(settings.tavily_api_key)
