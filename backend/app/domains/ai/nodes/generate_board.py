from __future__ import annotations

import logging
from typing import Any

from app.core.types import BoardSkeletonOutput, BoardSkeletonTaskOutput
from app.domains.ai.lang_utils import get_language_name
from app.domains.ai.llm import get_llm
from app.domains.ai.prompts.generate_board import (
    SKELETON_SYSTEM_PROMPT,
    SKELETON_USER_PROMPT,
    SUB_BOARD_SKELETON_SYSTEM_PROMPT,
    SUB_BOARD_SKELETON_USER_PROMPT,
)
from app.domains.ai.prompts.review_skeleton import (
    REVIEW_SKELETON_SYSTEM_PROMPT,
    REVIEW_SKELETON_USER_PROMPT,
)
from app.domains.ai.schemas import SkeletonReviewOutput

logger = logging.getLogger(__name__)


async def generate_board_skeleton(
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
    language: str = "en",
    user_context: str = "",
    memory_context: str = "",
    research_context: str = "",
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
        research_context=research_context,
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

    if result.reasoning:
        logger.debug("Skeleton reasoning: %s", result.reasoning)

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


# ── Skeleton Review ──────────────────────────────────────


async def review_skeleton(
    skeleton: BoardSkeletonOutput,
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
    language: str = "en",
    user_context: str = "",
    memory_context: str = "",
    research_context: str = "",
) -> BoardSkeletonOutput:
    """Review a skeleton against research context and optionally revise it.

    Returns the original skeleton if no issues, or a revised skeleton
    if significant problems were found. Runs exactly once (no loop).
    """
    # Skip review if there's no research context — nothing to review against
    if not research_context:
        logger.debug("Skipping skeleton review: no research context")
        return skeleton

    llm = get_llm()
    structured_llm = llm.with_structured_output(SkeletonReviewOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language_name = get_language_name(language)

    # Format skeleton tasks for the prompt
    skeleton_tasks_str = "\n".join(
        f'  - {t.id}: "{t.title}" '
        f"(depends_on: [{', '.join(t.depends_on)}]"
        f"{', is_goal_node' if t.is_goal_node else ''})"
        for t in skeleton.tasks
    )

    system_content = REVIEW_SKELETON_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
    )

    user_content = REVIEW_SKELETON_USER_PROMPT.format(
        raw_input=raw_input,
        domain=domain,
        complexity=complexity,
        dimensions=", ".join(dimensions),
        language=language,
        qa_pairs=qa_pairs,
        board_title=skeleton.board_title,
        skeleton_tasks=skeleton_tasks_str,
        research_context=research_context,
        user_context=user_context,
        memory_context=memory_context,
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    try:
        result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

        if not isinstance(result, SkeletonReviewOutput):
            logger.warning("Skeleton review returned unexpected type: %s", type(result))
            return skeleton

        if result.reasoning:
            logger.debug("Skeleton review reasoning: %s", result.reasoning)

        if result.issues:
            logger.info("Skeleton review found issues: %s", result.issues)

        if not result.has_issues or not result.revised_tasks:
            logger.debug("Skeleton review: no revision needed")
            return skeleton

        # Build a revised BoardSkeletonOutput from the review output
        revised_tasks = [
            BoardSkeletonTaskOutput(
                id=t.get("id", f"t{i + 1}"),
                title=t.get("title", ""),
                depends_on=t.get("depends_on", []),
                is_goal_node=t.get("is_goal_node", False),
            )
            for i, t in enumerate(result.revised_tasks)
        ]

        revised_skeleton = BoardSkeletonOutput(
            reasoning=result.reasoning,
            board_title=result.revised_board_title or skeleton.board_title,
            tasks=revised_tasks,
        )

        logger.info(
            "Skeleton revised: %d -> %d tasks",
            len(skeleton.tasks),
            len(revised_skeleton.tasks),
        )

        return revised_skeleton

    except Exception:
        logger.warning("Skeleton review failed, keeping original", exc_info=True)
        return skeleton
