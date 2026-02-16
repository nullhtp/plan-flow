from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.domains.ai.prompts.generate_board import (
    BOARD_GENERATION_SYSTEM_PROMPT,
    BOARD_GENERATION_USER_PROMPT,
)
from app.domains.ai.schemas import BoardGenerationOutput


def _get_llm() -> ChatOpenAI:
    """Create a LangChain chat model configured for board generation."""
    return ChatOpenAI(
        model=settings.ai_default_model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


async def generate_board(
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
) -> BoardGenerationOutput:
    """Generate a board structure using the LLM and return structured output."""
    llm = _get_llm()
    structured_llm = llm.with_structured_output(BoardGenerationOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    user_content = BOARD_GENERATION_USER_PROMPT.format(
        raw_input=raw_input,
        domain=domain,
        complexity=complexity,
        dimensions=", ".join(dimensions),
        qa_pairs=qa_pairs,
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": BOARD_GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, BoardGenerationOutput):
        msg = f"Expected BoardGenerationOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result
