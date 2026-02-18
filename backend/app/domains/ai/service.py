from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.core.types import BoardSkeletonOutput, TaskEnrichmentOutput
from app.domains.ai.nodes.classify import classify_goal
from app.domains.ai.nodes.enrich_task import enrich_task as _enrich_task
from app.domains.ai.nodes.generate_board import (
    generate_board_skeleton as _generate_skeleton,
)
from app.domains.ai.nodes.questions import (
    generate_follow_up_questions as _generate_follow_ups,
)
from app.domains.ai.nodes.questions import (
    generate_questions as _generate_questions,
)
from app.domains.ai.schemas import (
    ClassificationOutput,
    QuestionItem,
    SubtaskActionOutput,
    SubtaskActionsResponse,
)
from app.domains.boards.dag_utils import (
    CyclicDependencyError,
    GoalNodeValidationError,
    validate_dag,
    validate_goal_node,
)

logger = logging.getLogger(__name__)


class AIOutputError(Exception):
    """Raised when the AI produces invalid output after all retries."""


@dataclass
class ClassifyAndGenerateResult:
    """Result of the classify-and-generate pipeline."""

    classification: ClassificationOutput
    questions: list[QuestionItem]
    is_rejected: bool
    rejection_reason: str | None = None
    refinement_suggestions: list[str] | None = None


async def _retry_async(
    fn: Any,
    *args: Any,
    max_retries: int = settings.ai_max_retries,
) -> Any:
    """Retry an async function up to max_retries times on validation errors."""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await fn(*args)
        except (ValidationError, TypeError) as e:
            last_error = e
            logger.warning(
                "AI output validation failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )
    msg = f"AI output validation failed after {max_retries} attempts"
    raise AIOutputError(msg) from last_error


async def classify_and_generate_questions(
    raw_input: str,
    user_context: str = "",
    memory_context: str = "",
) -> ClassifyAndGenerateResult:
    """Run the full classify -> generate questions pipeline with retries."""
    classification: ClassificationOutput = await _retry_async(classify_goal, raw_input)

    if classification.confidence < settings.ai_confidence_threshold:
        return ClassifyAndGenerateResult(
            classification=classification,
            questions=[],
            is_rejected=True,
            rejection_reason=classification.rejection_reason
            or "This goal is too vague to create a meaningful plan.",
            refinement_suggestions=classification.refinement_suggestions,
        )

    questions: list[QuestionItem] = await _retry_async(
        _generate_questions, raw_input, classification, user_context, memory_context
    )

    return ClassifyAndGenerateResult(
        classification=classification,
        questions=questions,
        is_rejected=False,
    )


async def generate_follow_up_questions(
    raw_input: str,
    classification: ClassificationOutput,
    questions: list[QuestionItem],
    answers: dict[str, Any],
    user_context: str = "",
    memory_context: str = "",
) -> list[QuestionItem]:
    """Generate follow-up questions based on initial answers, with retries."""
    try:
        follow_ups: list[QuestionItem] = await _retry_async(
            _generate_follow_ups,
            raw_input,
            classification,
            questions,
            answers,
            user_context,
            memory_context,
        )
    except AIOutputError:
        logger.warning("Follow-up generation failed, proceeding without follow-ups")
        return []

    return follow_ups


# ── Subtask Action Generation ────────────────────────────


async def generate_subtask_actions(
    task_title: str,
    task_description: str,
    task_status: str,
    subtasks: list[dict[str, str]],
    model: str | None = None,
) -> list[SubtaskActionOutput]:
    """Generate actions for subtasks in a single batch LLM call.

    Each subtask gets at most one action. Non-automatable subtasks get null fields.
    Uses a lightweight structured-output LLM call (no tools, no graph).

    Args:
        task_title: Title of the parent task.
        task_description: Description of the parent task.
        task_status: Current status of the parent task.
        subtasks: List of dicts with at least a "title" key.
        model: Optional model override.

    Returns:
        List of SubtaskActionOutput, one per input subtask.
    """
    if not subtasks:
        return []

    from langchain_core.messages import HumanMessage, SystemMessage

    from app.domains.ai.llm import get_action_suggest_llm
    from app.domains.ai.prompts.action_suggestions import (
        SUBTASK_ACTIONS_SYSTEM_PROMPT,
        SUBTASK_ACTIONS_USER_PROMPT,
    )

    subtasks_formatted = "\n".join(f"- {s['title']}" for s in subtasks)

    system_prompt = SUBTASK_ACTIONS_SYSTEM_PROMPT.format(
        task_title=task_title,
        task_description=task_description or "No description provided",
        task_status=task_status,
        subtasks_list=subtasks_formatted,
    )

    llm = get_action_suggest_llm()
    structured_llm = llm.with_structured_output(SubtaskActionsResponse)

    async def _call() -> SubtaskActionsResponse:
        result = await structured_llm.ainvoke(  # pyright: ignore[reportUnknownMemberType]
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=SUBTASK_ACTIONS_USER_PROMPT),
            ]
        )
        if not isinstance(result, SubtaskActionsResponse):
            msg = f"Expected SubtaskActionsResponse, got {type(result)}"
            raise TypeError(msg)
        return result

    response: SubtaskActionsResponse = await _retry_async(_call)
    return response.actions


# ── Two-Step Board Generation (Streaming) ────────────────


def _validate_skeleton_dag(skeleton: BoardSkeletonOutput) -> None:
    """Validate that the skeleton output forms a valid DAG.

    Raises CyclicDependencyError or GoalNodeValidationError on failure.
    """
    task_ids = [t.id for t in skeleton.tasks]
    goal_flags = {t.id: t.is_goal_node for t in skeleton.tasks}
    task_id_set = set(task_ids)
    edges: list[tuple[str, str]] = []
    for t in skeleton.tasks:
        for dep_id in t.depends_on:
            if dep_id in task_id_set:
                edges.append((dep_id, t.id))

    validate_dag(task_ids, edges)
    validate_goal_node(task_ids, goal_flags, edges)


def _format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def generate_board_stream(
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
    language: str = "en",
    user_context: str = "",
    memory_context: str = "",
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted events for board generation.

    Events yielded:
    - skeleton_ready: Board skeleton with task IDs, titles, edges
    - task_enriched: Per-task enrichment (description, metadata, subtasks)
    - generation_complete: All done, with list of any failed task IDs
    - generation_error: Unrecoverable error
    """
    # ── Step 1: Generate skeleton with retries ──
    max_retries = settings.ai_max_retries
    skeleton: BoardSkeletonOutput | None = None
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            skeleton = await _generate_skeleton(
                raw_input,
                domain,
                complexity,
                dimensions,
                qa_pairs,
                language,
                user_context,
                memory_context,
            )
            _validate_skeleton_dag(skeleton)
            break
        except (ValidationError, TypeError) as e:
            last_error = e
            logger.warning(
                "Skeleton generation validation failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )
        except (CyclicDependencyError, GoalNodeValidationError) as e:
            last_error = e
            logger.warning(
                "Skeleton generated invalid DAG (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )

    if skeleton is None:
        yield _format_sse_event(
            "generation_error",
            {
                "error": "skeleton_generation_failed",
                "message": f"Board skeleton generation failed after {max_retries} attempts",  # noqa: E501
                "detail": str(last_error) if last_error else None,
            },
        )
        return

    # Build task ID -> title map and dependency info for enrichment context
    task_map = {t.id: t for t in skeleton.tasks}
    task_id_set = set(task_map.keys())

    # Build dependency and dependent title maps
    dependency_titles_map: dict[str, list[str]] = {t.id: [] for t in skeleton.tasks}
    dependent_titles_map: dict[str, list[str]] = {t.id: [] for t in skeleton.tasks}
    for t in skeleton.tasks:
        for dep_id in t.depends_on:
            if dep_id in task_id_set:
                dependency_titles_map[t.id].append(task_map[dep_id].title)
                dependent_titles_map[dep_id].append(t.title)

    # Yield skeleton_ready event
    skeleton_data = {
        "board_title": skeleton.board_title,
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "depends_on": t.depends_on,
                "is_goal_node": t.is_goal_node,
            }
            for t in skeleton.tasks
        ],
        "edges": [
            {"source": dep_id, "target": t.id}
            for t in skeleton.tasks
            for dep_id in t.depends_on
            if dep_id in task_id_set
        ],
    }
    yield _format_sse_event("skeleton_ready", skeleton_data)

    # ── Step 2: Parallel enrichment with concurrency limit ──
    semaphore = asyncio.Semaphore(settings.ai_enrichment_concurrency)
    failed_tasks: list[str] = []

    async def _enrich_single_task(
        ai_task_id: str,
    ) -> tuple[str, TaskEnrichmentOutput | None]:
        """Enrich a single task with retries, bounded by semaphore."""
        async with semaphore:
            last_err: Exception | None = None
            for attempt in range(max_retries):
                try:
                    result = await _enrich_task(
                        task_title=task_map[ai_task_id].title,
                        dependency_titles=dependency_titles_map[ai_task_id],
                        dependent_titles=dependent_titles_map[ai_task_id],
                        raw_input=raw_input,
                        domain=domain,
                        complexity=complexity,
                        language=language,
                        user_context=user_context,
                        memory_context=memory_context,
                    )
                    return ai_task_id, result
                except (ValidationError, TypeError) as e:
                    last_err = e
                    logger.warning(
                        "Task enrichment failed for '%s' (attempt %d/%d): %s",
                        ai_task_id,
                        attempt + 1,
                        max_retries,
                        str(e),
                    )

            logger.error(
                "Task enrichment failed for '%s' after %d attempts: %s",
                ai_task_id,
                max_retries,
                str(last_err),
            )
            return ai_task_id, None

    # Create all enrichment tasks
    tasks = [asyncio.create_task(_enrich_single_task(t.id)) for t in skeleton.tasks]

    # Yield task_enriched events as they complete
    for coro in asyncio.as_completed(tasks):
        ai_task_id, enrichment = await coro
        if enrichment is None:
            failed_tasks.append(ai_task_id)
            continue

        yield _format_sse_event(
            "task_enriched",
            {
                "task_id": ai_task_id,
                "description": enrichment.description,
                "due_date": enrichment.due_date,
                "priority": enrichment.priority,
                "estimated_minutes": enrichment.estimated_minutes,
                "subtasks": [{"title": s.title} for s in enrichment.subtasks],
            },
        )

    # ── Step 3: Generation complete ──
    yield _format_sse_event(
        "generation_complete",
        {
            "board_title": skeleton.board_title,
            "failed_tasks": failed_tasks,
        },
    )
