from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.domains.ai.lang_utils import get_language_name
from app.domains.ai.prompts.enrich_task import (
    ENRICHMENT_SYSTEM_PROMPT,
    ENRICHMENT_USER_PROMPT,
)
from app.domains.ai.schemas import TaskEnrichmentOutput


def _get_llm() -> ChatOpenAI:
    """Create a LangChain chat model configured for task enrichment."""
    return ChatOpenAI(
        model=settings.ai_default_model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


async def enrich_task(
    task_title: str,
    dependency_titles: list[str],
    dependent_titles: list[str],
    raw_input: str,
    domain: str,
    complexity: int,
    language: str = "en",
) -> TaskEnrichmentOutput:
    """Enrich a single task with description, metadata, and subtasks."""
    llm = _get_llm()
    structured_llm = llm.with_structured_output(TaskEnrichmentOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language_name = get_language_name(language)

    system_content = ENRICHMENT_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
    )

    user_content = ENRICHMENT_USER_PROMPT.format(
        raw_input=raw_input,
        domain=domain,
        complexity=complexity,
        language=language,
        task_title=task_title,
        dependency_titles=", ".join(dependency_titles)
        if dependency_titles
        else "None (root task)",
        dependent_titles=", ".join(dependent_titles)
        if dependent_titles
        else "None (leaf task)",
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, TaskEnrichmentOutput):
        msg = f"Expected TaskEnrichmentOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result
