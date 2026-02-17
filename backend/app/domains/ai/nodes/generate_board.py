from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.domains.ai.lang_utils import get_language_name
from app.domains.ai.prompts.generate_board import (
    SKELETON_SYSTEM_PROMPT,
    SKELETON_USER_PROMPT,
)
from app.domains.ai.schemas import BoardSkeletonOutput


def _get_llm() -> ChatOpenAI:
    """Create a LangChain chat model configured for board generation."""
    return ChatOpenAI(
        model=settings.ai_default_model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


async def generate_board_skeleton(
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
    language: str = "en",
    user_context: str = "",
    memory_context: str = "",
) -> BoardSkeletonOutput:
    """Generate a board skeleton (structure only) using the LLM."""
    llm = _get_llm()
    structured_llm = llm.with_structured_output(BoardSkeletonOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language_name = get_language_name(language)

    system_content = SKELETON_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
    )

    user_content = SKELETON_USER_PROMPT.format(
        raw_input=raw_input,
        domain=domain,
        complexity=complexity,
        dimensions=", ".join(dimensions),
        language=language,
        qa_pairs=qa_pairs,
        user_context=user_context,
        memory_context=memory_context,
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, BoardSkeletonOutput):
        msg = f"Expected BoardSkeletonOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result
