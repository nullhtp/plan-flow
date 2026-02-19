"""Task-level operations: CRUD, status validation, dependencies, generation."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import BoardSkeletonOutput, TaskEnrichmentOutput
from app.domains.boards.board_repository import BoardRepository
from app.domains.boards.dag_utils import validate_dag, validate_goal_node
from app.domains.boards.models import Board, Task
from app.domains.boards.ownership import (
    BoardNotFoundError,
    TaskNotFoundError,
    validate_board_ownership,
    validate_task_ownership,
)
from app.domains.boards.position_utils import generate_position_after
from app.domains.boards.subtask_repository import SubtaskRepository
from app.domains.boards.task_repository import TaskRepository
from app.domains.goals.models import Goal, GoalStatus

logger = logging.getLogger(__name__)


# ── Error Classes ────────────────────────────────────────


class BoardAlreadyExistsError(Exception):
    """Raised when a board already exists for the given goal."""


class GoalNotReadyError(Exception):
    """Raised when a goal is not in 'answered' status for board generation."""


class TaskStatusError(Exception):
    """Raised when a task status transition is invalid."""


class DependencyError(Exception):
    """Raised when dependency constraints are violated."""


# ── Task CRUD ────────────────────────────────────────────


async def create_task(
    session: AsyncSession,
    board_id: str,
    user_id: str,
    title: str,
    description: str = "",
    due_date: date | None = None,
    priority: str | None = None,
    estimated_minutes: int | None = None,
) -> Board:
    """Create a new task on a board. Returns refreshed board."""
    await validate_board_ownership(session, board_id, user_id)

    task = Task(
        board_id=board_id,
        title=title,
        description=description,
        status="not_started",
        due_date=due_date,
        priority=priority,
        estimated_minutes=estimated_minutes,
    )
    repo = TaskRepository(session)
    await repo.create(task)
    await session.commit()

    from app.domains.boards.board_service import get_board

    return await get_board(session, board_id, user_id)


async def update_task(
    session: AsyncSession,
    task_id: str,
    user_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    due_date: date | None = None,
    priority: str | None = None,
    estimated_minutes: int | None = None,
) -> Board:
    """Update task fields. Validates status transitions."""
    task = await validate_task_ownership(session, task_id, user_id)

    if status is not None and status != task.status:
        await _validate_status_transition(session, task, status)
        task.status = status

        # Completion propagation: if this is a goal node on a sub-board
        # that was just marked done, auto-complete the parent task
        if status == "done" and task.is_goal_node:
            await _propagate_sub_board_completion(session, task)

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if due_date is not None:
        task.due_date = due_date  # pyright: ignore[reportAttributeAccessIssue]
    if priority is not None:
        task.priority = priority
    if estimated_minutes is not None:
        task.estimated_minutes = estimated_minutes

    task.updated_at = datetime.now(UTC)
    repo = TaskRepository(session)
    await repo.update(task)
    await session.commit()

    from app.domains.boards.board_service import get_board

    return await get_board(session, task.board_id, user_id)


async def _validate_status_transition(
    session: AsyncSession, task: Task, new_status: str
) -> None:
    """Validate a task status transition.

    Rules:
    - not_started -> in_progress: requires all deps done
    - in_progress -> done: allowed
    - not_started -> done: rejected
    - done -> not_started/in_progress: allowed (undo)
    """
    valid_statuses = {"not_started", "in_progress", "done"}
    if new_status not in valid_statuses:
        raise TaskStatusError(f"Invalid status: {new_status}")

    repo = TaskRepository(session)

    if task.status == "not_started" and new_status == "in_progress":
        deps_met = await repo.are_dependencies_met(task.id)
        if not deps_met:
            raise TaskStatusError(
                "Cannot start task: not all dependencies are completed"
            )
    elif task.status == "not_started" and new_status == "done":
        raise TaskStatusError(
            "Cannot complete task directly: must be in progress first"
        )
    elif task.status == "in_progress" and new_status == "done":
        pass  # Always allowed
    elif task.status == "done" and new_status in ("not_started", "in_progress"):
        pass  # Allow undo


async def _propagate_sub_board_completion(
    session: AsyncSession, goal_task: Task
) -> None:
    """When a sub-board's goal node is marked done, auto-complete the parent task.

    The propagation bypasses the normal 'in_progress' prerequisite check
    since the sub-board completion proves the work is done.
    """
    board = await session.get(Board, goal_task.board_id)
    if board is None or board.parent_task_id is None:
        return  # Not a sub-board, nothing to propagate

    parent_task = await session.get(Task, board.parent_task_id)
    if parent_task is None or parent_task.status == "done":
        return  # Already done or deleted

    # Auto-complete the parent task (skip normal transition validation)
    parent_task.status = "done"
    parent_task.updated_at = datetime.now(UTC)
    task_repo = TaskRepository(session)
    await task_repo.update(parent_task)
    logger.info(
        "Auto-completed parent task '%s' via sub-board goal node completion",
        parent_task.id,
    )


async def delete_task(
    session: AsyncSession,
    task_id: str,
    user_id: str,
) -> Board:
    """Delete a task, its subtasks, and dependency edges. Returns refreshed board."""
    task = await validate_task_ownership(session, task_id, user_id)
    board_id = task.board_id

    repo = TaskRepository(session)
    await repo.delete(task)
    await session.commit()

    from app.domains.boards.board_service import get_board

    return await get_board(session, board_id, user_id)


# ── Dependency Query Helpers (public, for external callers) ──


async def get_task_dependencies(session: AsyncSession, task_id: str) -> list[Task]:
    """Return all prerequisite tasks for a given task."""
    repo = TaskRepository(session)
    return await repo.get_dependencies(task_id)


async def get_task_dependents(session: AsyncSession, task_id: str) -> list[Task]:
    """Return all tasks that depend on the given task."""
    repo = TaskRepository(session)
    return await repo.get_dependents(task_id)


async def are_dependencies_met(session: AsyncSession, task_id: str) -> bool:
    """Check if all prerequisite tasks have status 'done'."""
    repo = TaskRepository(session)
    return await repo.are_dependencies_met(task_id)


# ── Sub-Board Generation ─────────────────────────────────


class SubBoardAlreadyExistsError(Exception):
    """Raised when a sub-board already exists for the given task."""


class TaskLockedError(Exception):
    """Raised when the task is locked (dependencies not met)."""


async def create_sub_board_from_skeleton(
    session: AsyncSession,
    parent_task: Task,
    skeleton: BoardSkeletonOutput,
) -> tuple[Board, dict[str, str]]:
    """Persist sub-board skeleton as Board + Tasks + TaskDependency records.

    Similar to create_board_from_skeleton but sets parent_task_id instead of goal_id.
    Returns (sub_board, ai_id_to_db_id mapping).
    """
    board_repo = BoardRepository(session)
    task_repo = TaskRepository(session)

    sub_board = Board(
        parent_task_id=parent_task.id,
        title=skeleton.board_title,
    )
    await board_repo.create(sub_board)

    # Build mapping from AI task IDs to DB task IDs
    ai_id_to_db_id: dict[str, str] = {}
    ai_id_to_goal_flag: dict[str, bool] = {}
    edges: list[tuple[str, str]] = []

    for task_output in skeleton.tasks:
        task = Task(
            board_id=sub_board.id,
            title=task_output.title,
            description="",
            status="not_started",
            is_goal_node=task_output.is_goal_node,
        )
        await task_repo.create(task)
        ai_id_to_db_id[task_output.id] = task.id
        ai_id_to_goal_flag[task_output.id] = task_output.is_goal_node

    # Validate DAG structure
    all_ai_ids = list(ai_id_to_db_id.keys())
    for task_output in skeleton.tasks:
        for dep_id in task_output.depends_on:
            if dep_id in ai_id_to_db_id:
                edges.append((dep_id, task_output.id))

    validate_dag(all_ai_ids, edges)
    validate_goal_node(all_ai_ids, ai_id_to_goal_flag, edges)

    # Create dependency edges
    for dep_ai_id, dependent_ai_id in edges:
        dep_db_id = ai_id_to_db_id[dep_ai_id]
        dependent_db_id = ai_id_to_db_id[dependent_ai_id]
        await task_repo.create_dependency(dependent_db_id, dep_db_id)

    await session.commit()
    await session.refresh(sub_board)
    return sub_board, ai_id_to_db_id


async def delete_task_subtasks(session: AsyncSession, task: Task) -> None:
    """Delete all subtasks for a task (before sub-board creation)."""
    subtask_repo = SubtaskRepository(session)
    for subtask in list(task.subtasks):
        await subtask_repo.delete(subtask)
    # Clear the in-memory collection so the task object no longer
    # references the deleted Subtask instances (avoids
    # "Instance has been deleted" errors on subsequent session.add).
    task.subtasks.clear()
    await session.flush()


async def auto_start_parent_task(session: AsyncSession, task: Task) -> None:
    """Auto-transition a task to in_progress if it's not_started and deps are met."""
    if task.status != "not_started":
        return
    task_repo = TaskRepository(session)
    deps_met = await task_repo.are_dependencies_met(task.id)
    if deps_met:
        task.status = "in_progress"
        task.updated_at = datetime.now(UTC)
        await task_repo.update(task)
        logger.info("Auto-started parent task '%s' on sub-board creation", task.id)


# ── Board Generation (skeleton + enrichment) ─────────────


async def validate_goal_for_generation(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
) -> Goal:
    """Validate that a goal is ready for board generation.

    Pre-flight checks that run before the SSE stream starts,
    so errors can be returned as regular HTTP responses.

    Raises GoalNotReadyError if goal is not in 'answered' status.
    Raises BoardAlreadyExistsError if a board already exists.
    Raises BoardNotFoundError if goal not found or not owned by user.
    """
    goal = await session.get(Goal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError

    if goal.status != GoalStatus.ANSWERED.value:
        msg = f"Goal is in '{goal.status}' status, expected 'answered'"
        raise GoalNotReadyError(msg)

    # Check no board already exists
    repo = BoardRepository(session)
    existing = await repo.get_by_goal_id(goal_id)
    if existing is not None:
        raise BoardAlreadyExistsError

    return goal


async def create_board_from_skeleton(
    session: AsyncSession,
    goal_id: str,
    skeleton: BoardSkeletonOutput,
) -> tuple[Board, dict[str, str]]:
    """Persist skeleton as Board + Task (empty descriptions) + TaskDependency records.

    Phase 1 of two-phase persistence. Creates all records in a single transaction.
    Returns (board, ai_id_to_db_id mapping).
    """
    board_repo = BoardRepository(session)
    task_repo = TaskRepository(session)

    board = Board(
        goal_id=goal_id,
        title=skeleton.board_title,
    )
    await board_repo.create(board)

    # Build mapping from AI task IDs to DB task IDs
    ai_id_to_db_id: dict[str, str] = {}
    ai_id_to_goal_flag: dict[str, bool] = {}
    edges: list[tuple[str, str]] = []

    # Create all tasks (with titles only, empty descriptions)
    for task_output in skeleton.tasks:
        task = Task(
            board_id=board.id,
            title=task_output.title,
            description="",
            status="not_started",
            is_goal_node=task_output.is_goal_node,
        )
        await task_repo.create(task)

        ai_id_to_db_id[task_output.id] = task.id
        ai_id_to_goal_flag[task_output.id] = task_output.is_goal_node

    # Validate DAG structure
    all_ai_ids = list(ai_id_to_db_id.keys())
    for task_output in skeleton.tasks:
        for dep_id in task_output.depends_on:
            if dep_id in ai_id_to_db_id:
                edges.append((dep_id, task_output.id))

    # Run DAG validation
    validate_dag(all_ai_ids, edges)
    validate_goal_node(all_ai_ids, ai_id_to_goal_flag, edges)

    # Create dependency edges
    for dep_ai_id, dependent_ai_id in edges:
        dep_db_id = ai_id_to_db_id[dep_ai_id]
        dependent_db_id = ai_id_to_db_id[dependent_ai_id]
        await task_repo.create_dependency(dependent_db_id, dep_db_id)

    await session.commit()
    await session.refresh(board)
    return board, ai_id_to_db_id


async def update_task_with_enrichment(
    session: AsyncSession,
    task_id: str,
    enrichment: TaskEnrichmentOutput,
    user_context: str = "",
) -> list[str]:
    """Update a single Task record with enrichment data and create Subtask records.

    Phase 2 of two-phase persistence. Each call is its own transaction.
    After subtasks are created, generates AI actions for automatable subtasks
    (Phase 3 - graceful degradation on failure).
    Returns list of created subtask IDs.
    """
    task_repo = TaskRepository(session)
    subtask_repo = SubtaskRepository(session)

    task = await task_repo.get_by_id(task_id)
    if task is None:
        raise TaskNotFoundError

    # Update task fields
    task.description = enrichment.description
    task.updated_at = datetime.now(UTC)

    if enrichment.due_date is not None:
        try:
            task.due_date = date.fromisoformat(enrichment.due_date)  # pyright: ignore[reportAttributeAccessIssue]
        except ValueError:
            logger.warning(
                "Invalid due_date '%s' for task '%s', setting to null",
                enrichment.due_date,
                task.title,
            )
    if enrichment.priority is not None:
        task.priority = enrichment.priority
    if enrichment.estimated_minutes is not None:
        task.estimated_minutes = enrichment.estimated_minutes

    await task_repo.update(task)

    # Create subtask records with fractional index positions
    from app.domains.boards.models import Subtask

    subtask_ids: list[str] = []
    created_subtasks: list[Subtask] = []
    last_position: str | None = None
    for subtask_output in enrichment.subtasks:
        new_pos = generate_position_after(last_position)
        subtask = Subtask(
            task_id=task_id,
            title=subtask_output.title,
            position=new_pos,
        )
        await subtask_repo.create(subtask)
        subtask_ids.append(subtask.id)
        created_subtasks.append(subtask)
        last_position = new_pos

    await session.commit()

    # Phase 3: Generate AI actions for the created subtasks
    if created_subtasks:
        try:
            from app.domains.ai.service import generate_subtask_actions

            subtask_dicts = [{"title": s.title} for s in created_subtasks]
            actions = await generate_subtask_actions(
                task_title=task.title,
                task_description=task.description or "",
                task_status=task.status,
                subtasks=subtask_dicts,
                user_context=user_context,
            )

            # Match actions to subtasks by title and persist
            action_map = {a.subtask_title: a for a in actions}
            for subtask in created_subtasks:
                action = action_map.get(subtask.title)
                if action and action.action_label is not None:
                    subtask.action_label = action.action_label
                    subtask.action_icon = action.action_icon
                    subtask.action_prompt = action.action_prompt
                    session.add(subtask)

            await session.commit()
        except Exception:
            logger.exception(
                "Subtask action generation failed for task '%s' — "
                "subtasks created without actions",
                task.title,
            )

    return subtask_ids


# ── Board Generation Orchestration ───────────────────────


async def generate_board(
    session: AsyncSession,
    goal: Goal,
    user_id: str,
) -> Board:
    """Orchestrate full board generation: skeleton -> enrichment -> state transitions.

    This is the main entry point for board generation, extracted from the router.
    Handles AI streaming, DB persistence, goal state transitions, and memory extraction.
    """
    import json

    from app.domains.ai.schemas import ClassificationOutput
    from app.domains.ai.service import generate_board_stream
    from app.domains.boards.board_service import get_board
    from app.domains.goals.service import (
        revert_goal_to_answered,
        transition_goal_to_active,
        transition_goal_to_generating,
    )

    goal_id = goal.id

    # Transition goal to generating
    await transition_goal_to_generating(session, goal)

    # Extract context from ai_context
    ai_context: dict[str, Any] = dict(goal.ai_context)
    classification_data = ai_context.get("classification", {})
    classification = ClassificationOutput.model_validate(classification_data)

    from app.domains.boards.board_service import format_qa_pairs

    qa_pairs = format_qa_pairs(ai_context)
    language = classification.language

    # Format user meta for AI prompt injection
    from app.domains.ai.prompts.meta import format_user_meta_block

    user_context = format_user_meta_block(ai_context.get("user_meta"))

    # Retrieve memory context for board generation
    from app.core.config import settings as app_settings

    memory_context = ""
    if app_settings.ai_memory_enabled:
        from app.domains.ai.memory import retrieve_relevant_memories
        from app.domains.ai.prompts.memory import format_memory_block

        memories = await retrieve_relevant_memories(
            session, user_id, goal.original_input
        )
        memory_context = format_memory_block(memories)

    # Consume the AI streaming pipeline, persisting to DB as events arrive
    board: Board | None = None
    skeleton: BoardSkeletonOutput | None = None
    ai_id_to_db_id: dict[str, str] = {}

    async for sse_event in generate_board_stream(
        raw_input=goal.original_input,
        domain=classification.domain,
        complexity=classification.complexity,
        dimensions=classification.dimensions,
        qa_pairs=qa_pairs,
        language=language,
        user_context=user_context,
        memory_context=memory_context,
    ):
        # Parse the SSE event
        lines = sse_event.strip().split("\n")
        event_type = ""
        event_data: dict[str, Any] = {}
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                event_data = json.loads(line[6:])

        if event_type == "skeleton_ready":
            # Persist skeleton to database
            from app.domains.boards.dag_utils import (
                CyclicDependencyError,
                GoalNodeValidationError,
            )

            try:
                skel = BoardSkeletonOutput.model_validate(event_data)
                skeleton = skel
                board, ai_id_to_db_id = await create_board_from_skeleton(
                    session, goal_id, skel
                )
            except (CyclicDependencyError, GoalNodeValidationError) as e:
                logger.error("Skeleton persistence failed: %s", str(e))
                await revert_goal_to_answered(session, goal)
                raise BoardGenerationError(
                    f"Board skeleton generation produced invalid graph: {e}"
                ) from e
            except Exception as e:
                logger.error("Skeleton persistence failed: %s", str(e))
                await revert_goal_to_answered(session, goal)
                raise BoardGenerationError("Failed to persist board skeleton") from e

        elif event_type == "task_enriched":
            # Persist enrichment to database
            ai_task_id = event_data.get("task_id", "")
            db_task_id = ai_id_to_db_id.get(ai_task_id, "")

            if db_task_id:
                try:
                    enrichment = TaskEnrichmentOutput.model_validate(event_data)
                    await update_task_with_enrichment(
                        session, db_task_id, enrichment, user_context=user_context
                    )
                except Exception as e:
                    logger.error(
                        "Enrichment persistence failed for task '%s': %s",
                        ai_task_id,
                        str(e),
                    )

        elif event_type == "generation_complete":
            # Transition goal to active
            if board is not None:
                await transition_goal_to_active(session, goal)

                # Extract memories from board generation (best-effort)
                if app_settings.ai_memory_enabled:
                    try:
                        from app.domains.ai.memory import (
                            extract_memories_from_board,
                            store_memories_batch,
                        )

                        board_title = event_data.get("board_title", board.title)
                        task_count = len(skeleton.tasks) if skeleton else 0
                        mem_inputs = extract_memories_from_board(
                            board_title,
                            task_count,
                            classification.domain,
                            goal_id,
                        )
                        if mem_inputs:
                            await store_memories_batch(
                                session,
                                user_id,
                                mem_inputs,
                                source_goal_id=goal_id,
                            )
                            await session.commit()
                    except Exception:
                        logger.exception(
                            "Memory extraction after board generation failed"
                        )

        elif event_type == "generation_error":
            # Revert goal status and raise
            await revert_goal_to_answered(session, goal)
            error_msg = event_data.get("message", "Board generation failed")
            raise BoardGenerationError(error_msg)

    # If we never got a board (shouldn't happen if stream yields correctly)
    if board is None:
        await revert_goal_to_answered(session, goal)
        raise BoardGenerationError("Board generation produced no output")

    # Reload the board with all relationships for the response
    return await get_board(session, board.id, user_id)


async def generate_board_with_streaming(
    session: AsyncSession,
    goal: Goal,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """Orchestrate board generation, persisting to DB AND yielding SSE events to client.

    Same logic as generate_board() but yields client-facing SSE events for each stage.
    Client events have simplified payloads (titles + IDs only, no full enrichment data).
    """
    import json

    from app.domains.ai.schemas import ClassificationOutput
    from app.domains.ai.service import generate_board_stream
    from app.domains.goals.service import (
        revert_goal_to_answered,
        transition_goal_to_active,
        transition_goal_to_generating,
    )

    def _client_sse(event_type: str, data: dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    goal_id = goal.id

    # Transition goal to generating
    await transition_goal_to_generating(session, goal)

    # Extract context from ai_context
    ai_context: dict[str, Any] = dict(goal.ai_context)
    classification_data = ai_context.get("classification", {})
    classification = ClassificationOutput.model_validate(classification_data)

    from app.domains.boards.board_service import format_qa_pairs

    qa_pairs = format_qa_pairs(ai_context)
    language = classification.language

    from app.domains.ai.prompts.meta import format_user_meta_block

    user_context = format_user_meta_block(ai_context.get("user_meta"))

    from app.core.config import settings as app_settings

    memory_context = ""
    if app_settings.ai_memory_enabled:
        from app.domains.ai.memory import retrieve_relevant_memories
        from app.domains.ai.prompts.memory import format_memory_block

        memories = await retrieve_relevant_memories(
            session, user_id, goal.original_input
        )
        memory_context = format_memory_block(memories)

    board: Board | None = None
    skeleton: BoardSkeletonOutput | None = None
    ai_id_to_db_id: dict[str, str] = {}

    async for sse_event in generate_board_stream(
        raw_input=goal.original_input,
        domain=classification.domain,
        complexity=classification.complexity,
        dimensions=classification.dimensions,
        qa_pairs=qa_pairs,
        language=language,
        user_context=user_context,
        memory_context=memory_context,
    ):
        # Parse the internal SSE event
        lines = sse_event.strip().split("\n")
        event_type = ""
        event_data: dict[str, Any] = {}
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                event_data = json.loads(line[6:])

        if event_type == "skeleton_ready":
            from app.domains.boards.dag_utils import (
                CyclicDependencyError,
                GoalNodeValidationError,
            )

            try:
                skel = BoardSkeletonOutput.model_validate(event_data)
                skeleton = skel
                board, ai_id_to_db_id = await create_board_from_skeleton(
                    session, goal_id, skel
                )
            except (CyclicDependencyError, GoalNodeValidationError) as e:
                logger.error("Skeleton persistence failed: %s", str(e))
                await revert_goal_to_answered(session, goal)
                yield _client_sse(
                    "generation_error",
                    {"error": f"Invalid board structure: {e}"},
                )
                return
            except Exception as e:
                logger.error("Skeleton persistence failed: %s", str(e))
                await revert_goal_to_answered(session, goal)
                yield _client_sse(
                    "generation_error",
                    {"error": "Failed to create board structure"},
                )
                return

            # Forward skeleton to client with board_id
            yield _client_sse(
                "skeleton_ready",
                {
                    "board_id": board.id,
                    "board_title": skel.board_title,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "is_goal_node": t.is_goal_node,
                        }
                        for t in skel.tasks
                    ],
                },
            )

        elif event_type == "task_enriched":
            ai_task_id = event_data.get("task_id", "")
            db_task_id = ai_id_to_db_id.get(ai_task_id, "")

            if db_task_id:
                try:
                    enrichment = TaskEnrichmentOutput.model_validate(event_data)
                    await update_task_with_enrichment(
                        session, db_task_id, enrichment, user_context=user_context
                    )
                except Exception as e:
                    logger.error(
                        "Enrichment persistence failed for task '%s': %s",
                        ai_task_id,
                        str(e),
                    )

            # Forward enrichment event to client (lightweight)
            yield _client_sse(
                "task_enriched",
                {
                    "task_id": ai_task_id,
                    "title": event_data.get("title", ""),
                },
            )

        elif event_type == "generation_complete":
            if board is not None:
                await transition_goal_to_active(session, goal)

                if app_settings.ai_memory_enabled:
                    try:
                        from app.domains.ai.memory import (
                            extract_memories_from_board,
                            store_memories_batch,
                        )

                        board_title = event_data.get("board_title", board.title)
                        task_count = len(skeleton.tasks) if skeleton else 0
                        mem_inputs = extract_memories_from_board(
                            board_title,
                            task_count,
                            classification.domain,
                            goal_id,
                        )
                        if mem_inputs:
                            await store_memories_batch(
                                session,
                                user_id,
                                mem_inputs,
                                source_goal_id=goal_id,
                            )
                            await session.commit()
                    except Exception:
                        logger.exception(
                            "Memory extraction after board generation failed"
                        )

            yield _client_sse(
                "generation_complete",
                {
                    "board_id": board.id if board else "",
                    "failed_tasks": event_data.get("failed_tasks", []),
                },
            )

        elif event_type == "generation_error":
            await revert_goal_to_answered(session, goal)
            error_msg = event_data.get("message", "Board generation failed")
            yield _client_sse(
                "generation_error",
                {"error": error_msg},
            )
            return

    if board is None:
        await revert_goal_to_answered(session, goal)
        yield _client_sse(
            "generation_error",
            {"error": "Board generation produced no output"},
        )


async def generate_sub_board_with_streaming(
    session: AsyncSession,
    task: Task,
    board: Board,
    answers: list[dict[str, Any]],
    user_id: str,
) -> AsyncGenerator[str, None]:
    """Orchestrate sub-board generation, persisting to DB AND yielding SSE events.

    Same pattern as generate_board_with_streaming() but for sub-board expansion.
    Client events have simplified payloads (titles + IDs only).
    """
    import json

    from app.core.config import settings as app_settings
    from app.domains.ai.service import generate_sub_board_stream
    from app.domains.boards.dag_utils import (
        CyclicDependencyError,
        GoalNodeValidationError,
    )

    def _client_sse(event_type: str, data: dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    # Resolve goal context
    goal_id = board.goal_id
    goal = await session.get(Goal, goal_id) if goal_id else None  # type: ignore[arg-type]
    ai_context: dict[str, Any] = (
        dict(goal.ai_context) if goal and goal.ai_context else {}
    )
    classification_data = ai_context.get("classification", {})
    domain = classification_data.get("domain", "general")
    language = classification_data.get("language", "en")
    raw_input = goal.original_input if goal else task.title

    # Format Q&A pairs from answers
    answer_pairs: list[str] = []
    for a in answers:
        val = a["value"] if isinstance(a["value"], str) else str(a["value"])
        answer_pairs.append(f"Q ({a['question_id']}): ?\nA: {val}")
    qa_pairs = "\n\n".join(answer_pairs)

    from app.domains.ai.prompts.meta import format_user_meta_block

    user_context = format_user_meta_block(ai_context.get("user_meta")) or ""

    memory_context = ""
    if app_settings.ai_memory_enabled:
        from app.domains.ai.memory import retrieve_relevant_memories
        from app.domains.ai.prompts.memory import format_memory_block

        memories = await retrieve_relevant_memories(session, user_id, task.title)
        memory_context = format_memory_block(memories)

    # Delete existing subtasks before creating sub-board
    await delete_task_subtasks(session, task)

    # Auto-start parent task
    await auto_start_parent_task(session, task)
    await session.commit()

    sub_board: Board | None = None
    ai_id_to_db_id: dict[str, str] = {}

    async for sse_event in generate_sub_board_stream(
        task_title=task.title,
        task_description=task.description or "",
        board_title=board.title,
        raw_input=raw_input,
        domain=domain,
        qa_pairs=qa_pairs,
        language=language,
        user_context=user_context,
        memory_context=memory_context,
    ):
        # Parse the internal SSE event
        lines = sse_event.strip().split("\n")
        event_type = ""
        event_data: dict[str, Any] = {}
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                event_data = json.loads(line[6:])

        if event_type == "skeleton_ready":
            try:
                skel = BoardSkeletonOutput.model_validate(event_data)
                sub_board, ai_id_to_db_id = await create_sub_board_from_skeleton(
                    session, task, skel
                )
            except (CyclicDependencyError, GoalNodeValidationError) as e:
                logger.error("Sub-board skeleton persistence failed: %s", str(e))
                yield _client_sse(
                    "generation_error",
                    {"error": f"Invalid board structure: {e}"},
                )
                return
            except Exception as e:
                logger.error("Sub-board skeleton persistence failed: %s", str(e))
                yield _client_sse(
                    "generation_error",
                    {"error": "Failed to create board structure"},
                )
                return

            # Forward skeleton to client with board_id
            yield _client_sse(
                "skeleton_ready",
                {
                    "board_id": sub_board.id,
                    "board_title": skel.board_title,
                    "tasks": [
                        {
                            "id": t.id,
                            "title": t.title,
                            "is_goal_node": t.is_goal_node,
                        }
                        for t in skel.tasks
                    ],
                },
            )

        elif event_type == "task_enriched":
            ai_task_id = event_data.get("task_id", "")
            db_task_id = ai_id_to_db_id.get(ai_task_id, "")

            if db_task_id:
                try:
                    enrichment = TaskEnrichmentOutput.model_validate(event_data)
                    await update_task_with_enrichment(
                        session, db_task_id, enrichment, user_context=user_context
                    )
                except Exception as e:
                    logger.error(
                        "Sub-board enrichment failed for task '%s': %s",
                        ai_task_id,
                        str(e),
                    )

            # Forward enrichment event to client
            yield _client_sse(
                "task_enriched",
                {
                    "task_id": ai_task_id,
                    "title": event_data.get("title", ""),
                },
            )

        elif event_type == "generation_complete":
            yield _client_sse(
                "generation_complete",
                {
                    "board_id": sub_board.id if sub_board else "",
                    "failed_tasks": event_data.get("failed_tasks", []),
                },
            )

        elif event_type == "generation_error":
            error_msg = event_data.get("message", "Sub-board generation failed")
            yield _client_sse(
                "generation_error",
                {"error": error_msg},
            )
            return

    if sub_board is None:
        yield _client_sse(
            "generation_error",
            {"error": "Sub-board generation produced no output"},
        )


class BoardGenerationError(Exception):
    """Raised when board generation fails at any stage."""
