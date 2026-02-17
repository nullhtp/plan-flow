from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domains.ai.schemas import BoardSkeletonOutput, ClassificationOutput
from app.domains.ai.service import generate_board_stream
from app.domains.auth.deps import CurrentUser
from app.domains.boards.schemas import (
    BoardListResponse,
    BoardResponse,
    BoardUpdate,
    SubtaskCreate,
    SubtaskUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.domains.boards.service import (
    BoardAlreadyExistsError,
    BoardNotFoundError,
    GoalNotReadyError,
    SubtaskNotFoundError,
    TaskNotFoundError,
    TaskStatusError,
    _build_board_response,
    _format_qa_pairs,
    create_board_from_skeleton,
    create_subtask,
    create_task,
    delete_subtask,
    delete_task,
    get_board,
    get_user_meta_for_board,
    list_boards,
    revert_goal_to_answered,
    transition_goal_to_active,
    transition_goal_to_generating,
    update_board,
    update_subtask,
    update_task,
    update_task_with_enrichment,
    validate_goal_for_generation,
)

logger = logging.getLogger(__name__)

# Router for board CRUD endpoints (/api/boards/...)
router = APIRouter(prefix="/boards", tags=["boards"])

# Router for task endpoints (/api/tasks/...)
tasks_router = APIRouter(prefix="/tasks", tags=["boards"])

# Router for subtask endpoints (/api/subtasks/...)
subtasks_router = APIRouter(prefix="/subtasks", tags=["boards"])

# Router for goal-scoped board endpoints (/api/goals/:id/generate-board)
goals_router = APIRouter(prefix="/goals", tags=["boards"])


# ── Board Endpoints ──────────────────────────────────────


@router.get("", response_model=list[BoardListResponse])
async def list_boards_endpoint(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[BoardListResponse]:
    """List all boards for the authenticated user with summary stats."""
    boards = await list_boards(session, current_user.id)
    return [BoardListResponse(**b) for b in boards]


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board_endpoint(
    board_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Get a board by ID with nested tasks, dependencies, and edges."""
    try:
        board = await get_board(session, board_id, current_user.id)
    except BoardNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        ) from None

    user_meta = await get_user_meta_for_board(session, board)
    return _build_board_response(board, user_meta=user_meta)


@router.patch("/{board_id}", response_model=BoardResponse)
async def update_board_endpoint(
    board_id: str,
    body: BoardUpdate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Update a board's title."""
    try:
        board = await update_board(session, board_id, current_user.id, body.title)
    except BoardNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        ) from None

    return _build_board_response(board)


# ── Task Endpoints ───────────────────────────────────────


@router.post(
    "/{board_id}/tasks",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardResponse,
)
async def create_task_endpoint(
    board_id: str,
    body: TaskCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Create a new task on a board."""
    try:
        board = await create_task(
            session,
            board_id,
            current_user.id,
            title=body.title,
            description=body.description,
            due_date=body.due_date,
            priority=body.priority,
            estimated_minutes=body.estimated_minutes,
        )
    except BoardNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        ) from None

    return _build_board_response(board)


@tasks_router.patch("/{task_id}", response_model=BoardResponse)
async def update_task_endpoint(
    task_id: str,
    body: TaskUpdate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Update a task's fields. Handles status transitions with validation."""
    try:
        board = await update_task(
            session,
            task_id,
            current_user.id,
            title=body.title,
            description=body.description,
            status=body.status,
            due_date=body.due_date,
            priority=body.priority,
            estimated_minutes=body.estimated_minutes,
        )
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None
    except TaskStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None

    return _build_board_response(board)


@tasks_router.delete("/{task_id}", response_model=BoardResponse)
async def delete_task_endpoint(
    task_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Delete a task, its subtasks, and all dependency edges."""
    try:
        board = await delete_task(session, task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None

    return _build_board_response(board)


# ── Subtask Endpoints ────────────────────────────────────


@tasks_router.post(
    "/{task_id}/subtasks",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardResponse,
)
async def create_subtask_endpoint(
    task_id: str,
    body: SubtaskCreate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Create a new subtask for a task."""
    try:
        board = await create_subtask(session, task_id, current_user.id, body.title)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None

    return _build_board_response(board)


@subtasks_router.patch("/{subtask_id}", response_model=BoardResponse)
async def update_subtask_endpoint(
    subtask_id: str,
    body: SubtaskUpdate,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Update a subtask's title, completed status, or position."""
    try:
        board = await update_subtask(
            session,
            subtask_id,
            current_user.id,
            title=body.title,
            completed=body.completed,
            position=body.position,
        )
    except SubtaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subtask not found",
        ) from None

    return _build_board_response(board)


@subtasks_router.delete("/{subtask_id}", response_model=BoardResponse)
async def delete_subtask_endpoint(
    subtask_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Delete a subtask."""
    try:
        board = await delete_subtask(session, subtask_id, current_user.id)
    except SubtaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subtask not found",
        ) from None

    return _build_board_response(board)


# ── Goal-scoped Board Generation ─────────────────────────


@goals_router.post(
    "/{goal_id}/generate-board",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardResponse,
)
async def generate_board_endpoint(
    goal_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Generate a board for a goal using AI (two-step: skeleton + enrichment).

    Internally uses the streaming skeleton→enrichment pipeline but returns
    a standard JSON response with the fully-built board.
    """
    from app.domains.ai.schemas import TaskEnrichmentOutput
    from app.domains.boards.dag_utils import (
        CyclicDependencyError,
        GoalNodeValidationError,
    )

    # Pre-flight validation (returns regular HTTP errors)
    try:
        goal = await validate_goal_for_generation(session, goal_id, current_user.id)
    except BoardNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        ) from None
    except GoalNotReadyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None
    except BoardAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A board already exists for this goal",
        ) from None

    # Transition goal to generating
    await transition_goal_to_generating(session, goal)

    # Extract context from ai_context
    ai_context: dict[str, Any] = dict(goal.ai_context)
    classification_data = ai_context.get("classification", {})
    classification = ClassificationOutput.model_validate(classification_data)
    qa_pairs = _format_qa_pairs(ai_context)
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
            session, current_user.id, goal.original_input
        )
        memory_context = format_memory_block(memories)

    # Consume the AI streaming pipeline, persisting to DB as events arrive
    board = None
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
            try:
                skeleton = BoardSkeletonOutput.model_validate(event_data)
                board, ai_id_to_db_id = await create_board_from_skeleton(
                    session, goal_id, skeleton
                )
            except (CyclicDependencyError, GoalNodeValidationError) as e:
                logger.error("Skeleton persistence failed: %s", str(e))
                await revert_goal_to_answered(session, goal)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Board skeleton generation produced invalid graph: {e}",
                ) from None
            except Exception as e:
                logger.error("Skeleton persistence failed: %s", str(e))
                await revert_goal_to_answered(session, goal)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to persist board skeleton",
                ) from None

        elif event_type == "task_enriched":
            # Persist enrichment to database
            ai_task_id = event_data.get("task_id", "")
            db_task_id = ai_id_to_db_id.get(ai_task_id, "")

            if db_task_id:
                try:
                    enrichment = TaskEnrichmentOutput.model_validate(event_data)
                    await update_task_with_enrichment(session, db_task_id, enrichment)
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
                                current_user.id,
                                mem_inputs,
                                source_goal_id=goal_id,
                            )
                            await session.commit()
                    except Exception:
                        logger.exception(
                            "Memory extraction after board generation failed"
                        )

        elif event_type == "generation_error":
            # Revert goal status and raise HTTP error
            await revert_goal_to_answered(session, goal)
            error_msg = event_data.get("message", "Board generation failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

    # If we never got a board (shouldn't happen if stream yields correctly)
    if board is None:
        await revert_goal_to_answered(session, goal)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Board generation produced no output",
        )

    # Reload the board with all relationships for the response
    board = await get_board(session, board.id, current_user.id)
    board_user_meta = await get_user_meta_for_board(session, board)
    return _build_board_response(board, user_meta=board_user_meta)
