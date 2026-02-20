"""Shared research utilities for the AI pipeline.

Uses Perplexity Sonar (via LangChain ChatOpenAI) for web-grounded search.
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


def _get_perplexity_llm() -> ChatOpenAI:  # noqa: F821
    """Create a ChatOpenAI instance configured for Perplexity Sonar."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.perplexity_model,
        api_key=settings.perplexity_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://api.perplexity.ai",
        timeout=30.0,
    )


async def execute_search(
    query: str,
    max_results: int = 5,
) -> list[SearchResult]:
    """Execute a single web search via Perplexity Sonar.

    Perplexity returns a synthesized answer with citations rather than
    a list of ranked results. We convert the response into SearchResult
    objects: one for the synthesized answer, plus one per citation URL.

    Returns an empty list if Perplexity is not configured or the search fails.
    This is a standalone utility — not a LangChain tool.
    """
    if not settings.perplexity_api_key:
        return []

    try:
        llm = _get_perplexity_llm()
        response = await llm.ainvoke(
            [{"role": "user", "content": query}],
        )

        content = response.content if hasattr(response, "content") else str(response)

        # Extract citations from response metadata if available
        citations: list[str] = []
        if hasattr(response, "response_metadata"):
            citations = response.response_metadata.get("citations", [])

        results: list[SearchResult] = []

        # Primary result: the synthesized answer
        results.append(
            SearchResult(
                title=query,
                url=citations[0] if citations else "",
                content=str(content),
                score=1.0,
            )
        )

        # Additional results from citations (so downstream can fetch URLs)
        for i, url in enumerate(citations[:max_results]):
            if i == 0:
                continue  # Already used as primary result URL
            results.append(
                SearchResult(
                    title=f"Source: {url}",
                    url=url,
                    content="",  # Content available via fetch_top_urls
                    score=0.9 - (i * 0.1),
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
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                deduped.append(r)
            elif not r.url:
                # Keep results without URLs (synthesized answers)
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
    urls_to_fetch = [r.url for r in results[:limit] if r.url]

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
    """Check if web research is available (Perplexity configured)."""
    return bool(settings.perplexity_api_key)
