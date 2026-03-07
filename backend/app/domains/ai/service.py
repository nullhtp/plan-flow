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
from app.domains.ai.nodes.generate_board import (
    generate_sub_board_skeleton as _generate_sub_board_skeleton,
)
from app.domains.ai.nodes.generate_board import (
    review_skeleton as _review_skeleton,
)
from app.domains.ai.nodes.questions import (
    generate_follow_up_questions as _generate_follow_ups,
)
from app.domains.ai.nodes.questions import (
    generate_questions as _generate_questions,
)
from app.domains.ai.nodes.research import (
    ResearchEvent,
    run_pre_research,
    run_research,
)
from app.domains.ai.prompts.research import format_research_context
from app.domains.ai.research import ResearchContext
from app.domains.ai.schemas import (
    ClassificationOutput,
    QuestionItem,
    QuestionsOutput,
    ReadinessAssessment,
    SubtaskActionOutput,
    SubtaskActionsResponse,
    TemplateGenerationOutput,
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
    readiness: ReadinessAssessment | None = None


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
    """Run the full classify -> generate questions pipeline with retries.

    When Tavily is configured, runs a lightweight pre-research step (1-2 queries)
    to gather context before generating questions. Pre-research does NOT count
    against the main generation research budget.
    """
    classification: ClassificationOutput = await _retry_async(
        classify_goal, raw_input, user_context
    )

    if classification.confidence < settings.ai_confidence_threshold:
        return ClassifyAndGenerateResult(
            classification=classification,
            questions=[],
            is_rejected=True,
            rejection_reason=classification.rejection_reason
            or "This goal is too vague to create a meaningful plan.",
            refinement_suggestions=classification.refinement_suggestions,
        )

    # Run lightweight pre-research for better question quality
    pre_research_text = ""
    try:
        pre_research_ctx = await run_pre_research(
            raw_input=raw_input,
            domain=classification.domain,
            dimensions=classification.dimensions,
            language=classification.language,
        )
        pre_research_text = format_research_context(pre_research_ctx)
        if pre_research_text:
            logger.info(
                "Pre-research completed: %d results for question generation",
                len(pre_research_ctx.results),
            )
    except Exception:
        logger.warning(
            "Pre-research failed, generating questions without it", exc_info=True
        )

    questions_output: QuestionsOutput = await _retry_async(
        _generate_questions,
        raw_input,
        classification,
        user_context,
        memory_context,
        pre_research_text,
    )

    return ClassifyAndGenerateResult(
        classification=classification,
        questions=questions_output.questions,
        is_rejected=False,
        readiness=questions_output.readiness,
    )


async def generate_follow_up_questions(
    raw_input: str,
    classification: ClassificationOutput,
    rounds: list[dict[str, Any]],
    round_num: int,
    user_context: str = "",
    memory_context: str = "",
) -> QuestionsOutput | None:
    """Generate follow-up questions based on accumulated Q&A history, with retries.

    Args:
        raw_input: Original goal text.
        classification: Goal classification output.
        rounds: All rounds data (questions, answers, readiness).
        round_num: The next round number being generated.
        user_context: Formatted user meta block.
        memory_context: Formatted memory block.

    Returns QuestionsOutput with questions + readiness, or None on failure.
    """
    try:
        result: QuestionsOutput = await _retry_async(
            _generate_follow_ups,
            raw_input,
            classification,
            rounds,
            round_num,
            user_context,
            memory_context,
        )
    except AIOutputError:
        logger.warning("Follow-up generation failed, proceeding without follow-ups")
        return None

    return result


# ── Sub-Board Question Generation ────────────────────────


async def generate_sub_board_questions(
    task_title: str,
    task_description: str,
    board_title: str,
    goal_context: str,
    language: str,
    user_context: str | None = None,
    memory_context: str | None = None,
) -> list[QuestionItem]:
    """Generate 2-4 focused questions for decomposing a task into a sub-board.

    Single structured output LLM call — no LangGraph, no classification.
    """
    from app.domains.ai.lang_utils import get_language_name
    from app.domains.ai.llm import get_llm
    from app.domains.ai.prompts.sub_board_questions import (
        SUB_BOARD_QUESTIONS_SYSTEM_PROMPT,
        SUB_BOARD_QUESTIONS_USER_PROMPT,
    )

    language_name = get_language_name(language)

    system_content = SUB_BOARD_QUESTIONS_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
    )
    user_content = SUB_BOARD_QUESTIONS_USER_PROMPT.format(
        task_title=task_title,
        task_description=task_description or "No description provided",
        board_title=board_title,
        goal_context=goal_context,
        language=language,
        user_context=f"\nUser context: {user_context}" if user_context else "",
        memory_context=f"\nMemory context: {memory_context}" if memory_context else "",
    )

    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    async def _call() -> QuestionsOutput:
        result = await structured_llm.ainvoke(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ]
        )
        if not isinstance(result, QuestionsOutput):
            msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
            raise TypeError(msg)
        return result

    output: QuestionsOutput = await _retry_async(_call)

    # Ensure IDs are prefixed with "sbq" and count is 2-4
    questions = output.questions[:4]  # Cap at 4
    for i, q in enumerate(questions):
        if not q.id.startswith("sbq"):
            q.id = f"sbq{i + 1}"

    return questions


# ── Subtask Action Generation ────────────────────────────


async def generate_subtask_actions(
    task_title: str,
    task_description: str,
    task_status: str,
    subtasks: list[dict[str, str]],
    model: str | None = None,
    user_context: str = "",
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

    user_prompt = SUBTASK_ACTIONS_USER_PROMPT
    if user_context:
        user_prompt += f"\n{user_context}"

    async def _call() -> SubtaskActionsResponse:
        result = await structured_llm.ainvoke(  # pyright: ignore[reportUnknownMemberType]
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        if not isinstance(result, SubtaskActionsResponse):
            msg = f"Expected SubtaskActionsResponse, got {type(result)}"
            raise TypeError(msg)
        return result

    response: SubtaskActionsResponse = await _retry_async(_call)
    return response.actions


# ── Template Generation ───────────────────────────────────


async def generate_template_from_content(
    content: str,
    category_slugs: list[str],
    title_hint: str = "",
) -> TemplateGenerationOutput:
    """Generate a template DAG from text content using a single LLM call.

    Follows the same structured-output pattern as generate_subtask_actions.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.domains.ai.llm import get_llm
    from app.domains.ai.prompts.generate_template import (
        TEMPLATE_GENERATION_SYSTEM_PROMPT,
        TEMPLATE_GENERATION_USER_PROMPT,
    )
    from app.domains.ai.schemas import TemplateGenerationOutput

    system_prompt = TEMPLATE_GENERATION_SYSTEM_PROMPT.format(
        category_slugs=", ".join(category_slugs),
    )
    user_prompt = TEMPLATE_GENERATION_USER_PROMPT.format(
        content=content,
        title_hint=f"\nSuggested title: {title_hint}" if title_hint else "",
    )

    llm = get_llm()
    structured_llm = llm.with_structured_output(TemplateGenerationOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    async def _call() -> TemplateGenerationOutput:
        result = await structured_llm.ainvoke(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        if not isinstance(result, TemplateGenerationOutput):
            msg = f"Expected TemplateGenerationOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
            raise TypeError(msg)
        # Validate DAG structure
        _validate_template_dag(result)
        return result

    return await _retry_async(_call)


def _validate_template_dag(output: TemplateGenerationOutput) -> None:
    """Validate that the template generation output forms a valid DAG.

    Reuses the same dag_utils as board generation — DRY.
    """

    task_ids = [t.id for t in output.tasks]
    goal_flags = {t.id: t.is_goal_node for t in output.tasks}
    task_id_set = set(task_ids)
    edges: list[tuple[str, str]] = []
    for t in output.tasks:
        for dep_id in t.depends_on:
            if dep_id in task_id_set:
                edges.append((dep_id, t.id))

    validate_dag(task_ids, edges)
    validate_goal_node(task_ids, goal_flags, edges)


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
    - research_started: Research phase beginning (query count)
    - research_progress: Per-query search progress
    - research_complete: Research phase done (result summary)
    - skeleton_ready: Board skeleton with task IDs, titles, edges
    - task_enriched: Per-task enrichment (description, metadata, subtasks)
    - generation_complete: All done, with list of any failed task IDs
    - generation_error: Unrecoverable error
    """
    max_retries = settings.ai_max_retries

    # ── Step 0: Run research (if Tavily configured) ──
    research_ctx = ResearchContext()
    research_text = ""

    try:
        async for item in run_research(
            raw_input=raw_input,
            domain=domain,
            complexity=complexity,
            dimensions=dimensions,
            qa_pairs=qa_pairs,
            language=language,
            user_context=user_context,
            memory_context=memory_context,
        ):
            if isinstance(item, ResearchEvent):
                yield _format_sse_event(item.type, item.data)
            elif isinstance(item, ResearchContext):
                research_ctx = item
    except Exception:
        logger.warning(
            "Research phase failed, proceeding without research", exc_info=True
        )

    research_text = format_research_context(research_ctx)
    if research_text:
        logger.info(
            "Research completed: %d results from %d queries, %d URLs fetched",
            len(research_ctx.results),
            research_ctx.queries_used,
            len(research_ctx.fetched_contents),
        )

    # ── Step 1: Generate skeleton with retries ──
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
                research_context=research_text,
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

    # ── Step 1b: Review skeleton against research context ──
    if research_text:
        try:
            reviewed = await _review_skeleton(
                skeleton=skeleton,
                raw_input=raw_input,
                domain=domain,
                complexity=complexity,
                dimensions=dimensions,
                qa_pairs=qa_pairs,
                language=language,
                user_context=user_context,
                memory_context=memory_context,
                research_context=research_text,
            )
            # Validate revised skeleton if it changed
            if reviewed is not skeleton:
                try:
                    _validate_skeleton_dag(reviewed)
                    skeleton = reviewed
                except (CyclicDependencyError, GoalNodeValidationError) as e:
                    logger.warning(
                        "Revised skeleton failed DAG validation, keeping original: %s",
                        str(e),
                    )
        except Exception:
            logger.warning("Skeleton review failed, keeping original", exc_info=True)

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
                        research_context=research_text,
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


# ── Sub-Board Generation (Streaming) ────────────────────


async def generate_sub_board_stream(
    task_title: str,
    task_description: str,
    board_title: str,
    raw_input: str,
    domain: str,
    qa_pairs: str,
    language: str = "en",
    user_context: str = "",
    memory_context: str = "",
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events for sub-board generation.

    Same event format as generate_board_stream but uses the sub-board
    skeleton prompt (3-15 tasks instead of 5-30).
    """
    max_retries = settings.ai_max_retries
    skeleton: BoardSkeletonOutput | None = None
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            skeleton = await _generate_sub_board_skeleton(
                task_title=task_title,
                task_description=task_description,
                board_title=board_title,
                raw_input=raw_input,
                domain=domain,
                qa_pairs=qa_pairs,
                language=language,
                user_context=user_context,
                memory_context=memory_context,
            )
            _validate_skeleton_dag(skeleton)
            break
        except (ValidationError, TypeError) as e:
            last_error = e
            logger.warning(
                "Sub-board skeleton validation failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )
        except (CyclicDependencyError, GoalNodeValidationError) as e:
            last_error = e
            logger.warning(
                "Sub-board skeleton invalid DAG (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )

    if skeleton is None:
        yield _format_sse_event(
            "generation_error",
            {
                "error": "skeleton_generation_failed",
                "message": (
                    f"Sub-board skeleton generation failed after {max_retries} attempts"
                ),
                "detail": str(last_error) if last_error else None,
            },
        )
        return

    task_map = {t.id: t for t in skeleton.tasks}
    task_id_set = set(task_map.keys())

    dependency_titles_map: dict[str, list[str]] = {t.id: [] for t in skeleton.tasks}
    dependent_titles_map: dict[str, list[str]] = {t.id: [] for t in skeleton.tasks}
    for t in skeleton.tasks:
        for dep_id in t.depends_on:
            if dep_id in task_id_set:
                dependency_titles_map[t.id].append(task_map[dep_id].title)
                dependent_titles_map[dep_id].append(t.title)

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

    # Parallel enrichment
    semaphore = asyncio.Semaphore(settings.ai_enrichment_concurrency)
    failed_tasks: list[str] = []

    async def _enrich_single_task(
        ai_task_id: str,
    ) -> tuple[str, TaskEnrichmentOutput | None]:
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
                        complexity=3,  # Sub-boards are mid-complexity
                        language=language,
                        user_context=user_context,
                        memory_context=memory_context,
                    )
                    return ai_task_id, result
                except (ValidationError, TypeError) as e:
                    last_err = e
                    logger.warning(
                        "Sub-board task enrichment failed for '%s' (attempt %d/%d): %s",
                        ai_task_id,
                        attempt + 1,
                        max_retries,
                        str(e),
                    )
            logger.error(
                "Sub-board task enrichment failed for '%s' after %d attempts: %s",
                ai_task_id,
                max_retries,
                str(last_err),
            )
            return ai_task_id, None

    tasks = [asyncio.create_task(_enrich_single_task(t.id)) for t in skeleton.tasks]

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

    yield _format_sse_event(
        "generation_complete",
        {
            "board_title": skeleton.board_title,
            "failed_tasks": failed_tasks,
        },
    )


# ── Template Streaming Generation ────────────────────────


async def generate_template_stream(
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
    language: str = "en",
    content: str | None = None,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events for template generation.

    Mirrors generate_board_stream: research -> skeleton -> review -> enrichment.
    Uses template-specific prompts for more generic/reusable output.

    Events yielded:
    - research_started, research_progress, research_complete
    - skeleton_ready: Template skeleton with task IDs, titles, edges
    - task_enriched: Per-task enrichment (description, metadata, subtasks)
    - generation_complete: All done
    - generation_error: Unrecoverable error
    """
    from app.domains.ai.lang_utils import get_language_name
    from app.domains.ai.llm import get_llm
    from app.domains.ai.prompts.generate_template_questions import (
        format_template_content_context,
    )
    from app.domains.ai.prompts.generate_template_skeleton import (
        TEMPLATE_SKELETON_SYSTEM_PROMPT,
        TEMPLATE_SKELETON_USER_PROMPT,
    )

    max_retries = settings.ai_max_retries

    # Format content context for prompts
    content_context = format_template_content_context(content) if content else ""

    # ── Step 0: Run research (if Tavily configured) ──
    research_ctx = ResearchContext()
    research_text = ""

    try:
        async for item in run_research(
            raw_input=raw_input,
            domain=domain,
            complexity=complexity,
            dimensions=dimensions,
            qa_pairs=qa_pairs,
            language=language,
        ):
            if isinstance(item, ResearchEvent):
                yield _format_sse_event(item.type, item.data)
            elif isinstance(item, ResearchContext):
                research_ctx = item
    except Exception:
        logger.warning(
            "Template research phase failed, proceeding without research",
            exc_info=True,
        )

    research_text = format_research_context(research_ctx)
    if research_text:
        logger.info(
            "Template research completed: %d results from %d queries",
            len(research_ctx.results),
            research_ctx.queries_used,
        )

    # ── Step 1: Generate skeleton with template-specific prompt ──
    language_name = get_language_name(language)
    skeleton: BoardSkeletonOutput | None = None
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            llm = get_llm()
            structured_llm = llm.with_structured_output(BoardSkeletonOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

            system_content = TEMPLATE_SKELETON_SYSTEM_PROMPT.format(
                language=language,
                language_name=language_name,
            )
            user_content = TEMPLATE_SKELETON_USER_PROMPT.format(
                raw_input=raw_input,
                domain=domain,
                complexity=complexity,
                dimensions=", ".join(dimensions),
                language=language,
                qa_pairs=qa_pairs,
                content_context=content_context,
                research_context=research_text,
            )

            result = await structured_llm.ainvoke(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ]
            )
            if not isinstance(result, BoardSkeletonOutput):
                msg = f"Expected BoardSkeletonOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
                raise TypeError(msg)
            skeleton = result
            _validate_skeleton_dag(skeleton)
            break
        except (ValidationError, TypeError) as e:
            last_error = e
            logger.warning(
                "Template skeleton validation failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )
        except (CyclicDependencyError, GoalNodeValidationError) as e:
            last_error = e
            logger.warning(
                "Template skeleton invalid DAG (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )

    if skeleton is None:
        yield _format_sse_event(
            "generation_error",
            {
                "error": "skeleton_generation_failed",
                "message": (
                    f"Template skeleton generation failed after {max_retries} attempts"
                ),
                "detail": str(last_error) if last_error else None,
            },
        )
        return

    # ── Step 1b: Review skeleton against research context ──
    if research_text:
        try:
            reviewed = await _review_skeleton(
                skeleton=skeleton,
                raw_input=raw_input,
                domain=domain,
                complexity=complexity,
                dimensions=dimensions,
                qa_pairs=qa_pairs,
                language=language,
            )
            if reviewed is not skeleton:
                try:
                    _validate_skeleton_dag(reviewed)
                    skeleton = reviewed
                except (CyclicDependencyError, GoalNodeValidationError) as e:
                    logger.warning(
                        "Revised template skeleton failed DAG validation, "
                        "keeping original: %s",
                        str(e),
                    )
        except Exception:
            logger.warning(
                "Template skeleton review failed, keeping original",
                exc_info=True,
            )

    # Build task maps for enrichment context
    task_map = {t.id: t for t in skeleton.tasks}
    task_id_set = set(task_map.keys())

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

    # ── Step 2: Parallel enrichment ──
    semaphore = asyncio.Semaphore(settings.ai_enrichment_concurrency)
    failed_tasks: list[str] = []

    async def _enrich_single_task(
        ai_task_id: str,
    ) -> tuple[str, TaskEnrichmentOutput | None]:
        async with semaphore:
            last_err: Exception | None = None
            for attempt in range(max_retries):
                try:
                    enrichment_result = await _enrich_task(
                        task_title=task_map[ai_task_id].title,
                        dependency_titles=dependency_titles_map[ai_task_id],
                        dependent_titles=dependent_titles_map[ai_task_id],
                        raw_input=raw_input,
                        domain=domain,
                        complexity=complexity,
                        language=language,
                        research_context=research_text,
                    )
                    return ai_task_id, enrichment_result
                except (ValidationError, TypeError) as e:
                    last_err = e
                    logger.warning(
                        "Template task enrichment failed for '%s' (attempt %d/%d): %s",
                        ai_task_id,
                        attempt + 1,
                        max_retries,
                        str(e),
                    )
            logger.error(
                "Template task enrichment failed for '%s' after %d attempts: %s",
                ai_task_id,
                max_retries,
                str(last_err),
            )
            return ai_task_id, None

    tasks = [asyncio.create_task(_enrich_single_task(t.id)) for t in skeleton.tasks]

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

    yield _format_sse_event(
        "generation_complete",
        {
            "board_title": skeleton.board_title,
            "failed_tasks": failed_tasks,
        },
    )


# ── Template Classification & Question Pipeline ─────────


@dataclass
class TemplateClassifyResult:
    """Result of the template classify pipeline."""

    classification: ClassificationOutput
    questions: list[QuestionItem]
    is_rejected: bool
    rejection_reason: str | None = None
    refinement_suggestions: list[str] | None = None
    readiness: ReadinessAssessment | None = None


async def classify_template_content(
    raw_input: str,
    input_type: str = "describe",
    content: str | None = None,
    title_hint: str | None = None,
) -> ClassificationOutput:
    """Classify template input using the LLM.

    Supports both description-based and content-based inputs.

    Args:
        raw_input: The user's description or a summary of the content.
        input_type: One of 'describe', 'text', 'file', 'url'.
        content: The extracted content (for text/file/url inputs).
        title_hint: Optional title hint from the user.

    Returns:
        ClassificationOutput with domain, complexity, confidence, etc.
    """
    from app.domains.ai.llm import get_llm
    from app.domains.ai.prompts.generate_template_questions import (
        TEMPLATE_CLASSIFICATION_SYSTEM_PROMPT,
        TEMPLATE_CLASSIFICATION_USER_PROMPT_CONTENT,
        TEMPLATE_CLASSIFICATION_USER_PROMPT_DESCRIBE,
    )

    llm = get_llm()
    structured_llm = llm.with_structured_output(ClassificationOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if input_type == "describe":
        user_content = TEMPLATE_CLASSIFICATION_USER_PROMPT_DESCRIBE.format(
            raw_input=raw_input,
        )
    else:
        # For text/file/url inputs, use the content-based prompt
        source_content = content or raw_input
        title_line = f"\nTitle hint: {title_hint}" if title_hint else ""
        user_content = TEMPLATE_CLASSIFICATION_USER_PROMPT_CONTENT.format(
            content=source_content[:15000],  # Truncate for context limits
            title_hint=title_line,
        )

    messages = [
        {"role": "system", "content": TEMPLATE_CLASSIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    async def _call() -> ClassificationOutput:
        result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(result, ClassificationOutput):
            msg = f"Expected ClassificationOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
            raise TypeError(msg)
        return result

    return await _retry_async(_call)


async def generate_template_questions(
    raw_input: str,
    classification: ClassificationOutput,
    content: str | None = None,
) -> QuestionsOutput:
    """Generate initial questions for a template based on classification.

    Args:
        raw_input: The user's original input (description or content summary).
        classification: Classification output from classify_template_content.
        content: Optional source content for context.

    Returns:
        QuestionsOutput with questions and initial readiness assessment.
    """
    from app.domains.ai.lang_utils import get_language_name
    from app.domains.ai.llm import get_llm
    from app.domains.ai.prompts.generate_template_questions import (
        TEMPLATE_QUESTIONS_USER_PROMPT,
        build_template_system_prompt,
        format_template_content_context,
    )

    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language = classification.language
    language_name = get_language_name(language)

    content_context = format_template_content_context(content)

    user_content = TEMPLATE_QUESTIONS_USER_PROMPT.format(
        raw_input=raw_input,
        domain=classification.domain,
        complexity=classification.complexity,
        dimensions=", ".join(classification.dimensions),
        language=language,
        qa_history="",
        content_context=content_context,
    )

    system_content = build_template_system_prompt(
        language=language,
        language_name=language_name,
        round_num=1,
        has_content=bool(content),
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    async def _call() -> QuestionsOutput:
        result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(result, QuestionsOutput):
            msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
            raise TypeError(msg)
        if result.reasoning:
            logger.debug("Template questions reasoning: %s", result.reasoning)
        return result

    return await _retry_async(_call)


async def generate_template_follow_up_questions(
    raw_input: str,
    classification: ClassificationOutput,
    rounds: list[dict[str, Any]],
    content: str | None = None,
) -> QuestionsOutput | None:
    """Generate follow-up questions for a template (max 1 follow-up round).

    Args:
        raw_input: Original template input text.
        classification: Template classification output.
        rounds: All rounds data (questions, answers, readiness).
        content: Optional source content for context.

    Returns:
        QuestionsOutput with questions + readiness, or None on failure.
    """
    from app.domains.ai.lang_utils import get_language_name
    from app.domains.ai.llm import get_llm
    from app.domains.ai.prompts.generate_template_questions import (
        TEMPLATE_QUESTIONS_USER_PROMPT,
        build_template_system_prompt,
        format_template_content_context,
    )
    from app.domains.ai.prompts.questions import format_qa_history

    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language = classification.language
    language_name = get_language_name(language)

    qa_history = format_qa_history(rounds)
    content_context = format_template_content_context(content)

    user_content = TEMPLATE_QUESTIONS_USER_PROMPT.format(
        raw_input=raw_input,
        domain=classification.domain,
        complexity=classification.complexity,
        dimensions=", ".join(classification.dimensions),
        language=language,
        qa_history=qa_history,
        content_context=content_context,
    )

    system_content = build_template_system_prompt(
        language=language,
        language_name=language_name,
        round_num=2,  # Always round 2 since we only allow 1 follow-up
        has_content=bool(content),
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    async def _call() -> QuestionsOutput:
        result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(result, QuestionsOutput):
            msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
            raise TypeError(msg)
        if result.reasoning:
            logger.debug("Template follow-up questions reasoning: %s", result.reasoning)
        return result

    try:
        return await _retry_async(_call)
    except AIOutputError:
        logger.warning(
            "Template follow-up generation failed, proceeding without follow-ups"
        )
        return None
