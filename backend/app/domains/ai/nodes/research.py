"""Research node for the AI generation pipeline.

Generates search queries via LLM, executes them in parallel,
fetches top URLs, and compiles a ResearchContext.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.domains.ai.llm import get_llm
from app.domains.ai.prompts.research import (
    RESEARCH_QUERIES_SYSTEM_PROMPT,
    RESEARCH_QUERIES_USER_PROMPT,
)
from app.domains.ai.research import (
    ResearchContext,
    SearchResult,
    execute_search,
    execute_searches_parallel,
    fetch_top_urls,
    is_research_available,
)
from app.domains.ai.schemas import ResearchQueriesOutput

logger = logging.getLogger(__name__)


@dataclass
class ResearchEvent:
    """An event yielded during research for SSE streaming."""

    type: str  # research_started, research_progress, research_complete
    data: dict[str, Any]


async def run_research(
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
    language: str = "en",
    user_context: str = "",
    memory_context: str = "",
    budget: int | None = None,
    max_queries: int = 8,
) -> AsyncGenerator[ResearchEvent | ResearchContext, None]:
    """Run the research node, yielding progress events and finally the context.

    This is an async generator that yields:
    - ResearchEvent objects for SSE streaming
    - A final ResearchContext as the last yielded item

    Args:
        raw_input: Original goal text.
        domain: Goal domain from classification.
        complexity: Goal complexity (1-5).
        dimensions: Key dimensions from classification.
        qa_pairs: Formatted Q&A pairs.
        language: Detected language code.
        user_context: Formatted user meta block.
        memory_context: Formatted memory block.
        budget: Total query budget (defaults to settings).
        max_queries: Max queries to generate for this phase.
    """
    total_budget = budget if budget is not None else settings.ai_max_research_queries

    if not is_research_available() or total_budget <= 0:
        yield ResearchContext(budget_remaining=total_budget)
        return

    # Step 1: Generate search queries via LLM
    query_count = min(max_queries, total_budget)

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(ResearchQueriesOutput)

        user_content = RESEARCH_QUERIES_USER_PROMPT.format(
            raw_input=raw_input,
            domain=domain,
            complexity=complexity,
            dimensions=", ".join(dimensions),
            language=language,
            qa_pairs=qa_pairs,
            user_context=user_context,
            memory_context=memory_context,
            query_count=query_count,
        )

        result = await structured_llm.ainvoke(
            [
                {"role": "system", "content": RESEARCH_QUERIES_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]
        )

        if not isinstance(result, ResearchQueriesOutput):
            logger.warning(
                "Research query generation returned unexpected type: %s", type(result)
            )
            yield ResearchContext(budget_remaining=total_budget)
            return

        queries = result.queries[:query_count]

    except Exception:
        logger.warning("Research query generation failed", exc_info=True)
        yield ResearchContext(budget_remaining=total_budget)
        return

    if not queries:
        yield ResearchContext(budget_remaining=total_budget)
        return

    # Yield research_started event
    yield ResearchEvent(
        type="research_started",
        data={"query_count": len(queries)},
    )

    # Step 2: Execute searches in parallel
    all_results: list[SearchResult] = []
    queries_completed = 0

    for query in queries:
        try:
            results = await execute_search(query, max_results=5)
            all_results.extend(results)
            queries_completed += 1

            yield ResearchEvent(
                type="research_progress",
                data={
                    "query": query,
                    "results_count": len(results),
                    "queries_completed": queries_completed,
                },
            )
        except Exception:
            logger.warning("Search failed for query: %s", query, exc_info=True)
            queries_completed += 1

    # Deduplicate by URL
    seen_urls: set[str] = set()
    deduped: list[SearchResult] = []
    for r in all_results:
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            deduped.append(r)
    deduped.sort(key=lambda r: r.score, reverse=True)

    # Step 3: Fetch top URLs for full content
    fetched_contents = await fetch_top_urls(deduped)

    budget_remaining = total_budget - len(queries)

    # Yield research_complete event
    yield ResearchEvent(
        type="research_complete",
        data={
            "total_results": len(deduped),
            "total_queries": len(queries),
            "urls_fetched": len(fetched_contents),
        },
    )

    # Yield the final ResearchContext
    yield ResearchContext(
        results=deduped,
        queries_used=len(queries),
        budget_remaining=max(0, budget_remaining),
        fetched_contents=fetched_contents,
    )


async def run_pre_research(
    raw_input: str,
    domain: str,
    dimensions: list[str],
    language: str = "en",
) -> ResearchContext:
    """Run lightweight pre-research (1-2 queries) for question generation.

    This does NOT count against the main research budget.
    Returns a ResearchContext, or an empty one on failure.
    """
    if not is_research_available():
        return ResearchContext()

    # Generate 1-2 simple queries based on the goal domain
    queries = [
        f"{raw_input} guide {language}",
        f"{domain} planning checklist 2026",
    ]
    queries = queries[:2]

    results = await execute_searches_parallel(queries, max_results_per_query=3)

    return ResearchContext(
        results=results[:6],
        queries_used=len(queries),
        budget_remaining=0,  # Pre-research doesn't track budget
    )
