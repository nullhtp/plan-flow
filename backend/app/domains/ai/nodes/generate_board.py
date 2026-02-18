from __future__ import annotations

from typing import Any

from app.core.types import BoardSkeletonOutput
from app.domains.ai.lang_utils import get_language_name
from app.domains.ai.llm import get_llm
from app.domains.ai.prompts.generate_board import (
    SKELETON_SYSTEM_PROMPT,
    SKELETON_USER_PROMPT,
    SUB_BOARD_SKELETON_SYSTEM_PROMPT,
    SUB_BOARD_SKELETON_USER_PROMPT,
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
    llm = get_llm()
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


async def generate_sub_board_skeleton(
    task_title: str,
    task_description: str,
    board_title: str,
    raw_input: str,
    domain: str,
    qa_pairs: str,
    language: str = "en",
    user_context: str = "",
    memory_context: str = "",
) -> BoardSkeletonOutput:
    """Generate a sub-board skeleton for decomposing a single task.

    Uses a variant prompt that produces 3-15 tasks (smaller than root boards).
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(BoardSkeletonOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language_name = get_language_name(language)

    system_content = SUB_BOARD_SKELETON_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
    )

    user_content = SUB_BOARD_SKELETON_USER_PROMPT.format(
        task_title=task_title,
        task_description=task_description or "No description provided",
        board_title=board_title,
        raw_input=raw_input,
        domain=domain,
        language=language,
        qa_pairs=qa_pairs,
        user_context=f"\nUser context: {user_context}" if user_context else "",
        memory_context=f"\nMemory context: {memory_context}" if memory_context else "",
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
