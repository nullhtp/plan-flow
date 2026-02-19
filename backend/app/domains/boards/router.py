from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domains.auth.deps import CurrentUser
from app.domains.boards.artifact_service import (
    delete_artifact,
    list_artifacts,
)
from app.domains.boards.board_service import (
    build_board_response,
    get_board,
    get_user_meta_for_board,
    list_boards,
    update_board,
)
from app.domains.boards.ownership import (
    ArtifactNotFoundError,
    BoardNotFoundError,
    SubtaskNotFoundError,
    TaskNotFoundError,
    validate_artifact_ownership,
    validate_task_ownership,
)
from app.domains.boards.schemas import (
    ArtifactListResponse,
    ArtifactResponse,
    BoardListResponse,
    BoardResponse,
    BoardUpdate,
    SubBoardGenerateRequest,
    SubBoardQuestionsResponse,
    SubtaskCreate,
    SubtaskUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.domains.boards.subtask_service import (
    create_subtask,
    delete_subtask,
    update_subtask,
)
from app.domains.boards.task_service import (
    BoardAlreadyExistsError,
    BoardGenerationError,
    GoalNotReadyError,
    TaskStatusError,
    create_task,
    delete_task,
    generate_board,
    update_task,
    validate_goal_for_generation,
)
from app.domains.goals.models import Goal

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

    # For sub-boards, resolve parent board for breadcrumb navigation
    from app.domains.boards.board_repository import BoardRepository

    parent_board = None
    if board.parent_task_id is not None:
        repo = BoardRepository(session)
        parent_board = await repo.get_parent_board(board)

    return build_board_response(board, user_meta=user_meta, parent_board=parent_board)


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

    return build_board_response(board)


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

    return build_board_response(board)


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

    return build_board_response(board)


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

    return build_board_response(board)


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

    return build_board_response(board)


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

    return build_board_response(board)


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

    return build_board_response(board)


# ── Sub-Board Endpoints ──────────────────────────────────


@tasks_router.post(
    "/{task_id}/sub-board-questions",
    response_model=SubBoardQuestionsResponse,
)
async def sub_board_questions_endpoint(
    task_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubBoardQuestionsResponse:
    """Generate 2-4 focused questions for decomposing a task into a sub-board."""
    try:
        task = await validate_task_ownership(session, task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None

    # Validate: task must be on a root board
    from app.domains.boards.dag_utils import NestingDepthError, validate_nesting_depth
    from app.domains.boards.models import Board

    board = await session.get(Board, task.board_id)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        )

    try:
        validate_nesting_depth(board)
    except NestingDepthError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sub-boards cannot be nested. This task belongs to a sub-board.",
        ) from None

    # Validate: task must not already have a sub-board
    from app.domains.boards.board_repository import BoardRepository

    repo = BoardRepository(session)
    existing_sub_board = await repo.get_sub_board_by_parent_task(task_id)
    if existing_sub_board is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sub-board already exists for this task",
        )

    # Resolve goal context for AI prompts
    from app.domains.boards.board_service import format_qa_pairs

    goal_id = board.goal_id
    goal = await session.get(Goal, goal_id) if goal_id else None  # type: ignore[arg-type]

    ai_context = dict(goal.ai_context) if goal and goal.ai_context else {}
    goal_context = ai_context.get("classification", {}).get("domain", "")
    qa_pairs = format_qa_pairs(ai_context) if ai_context else ""
    language = ai_context.get("classification", {}).get("language", "en")

    # Format user context
    from app.domains.ai.prompts.meta import format_user_meta_block

    user_context = format_user_meta_block(ai_context.get("user_meta"))

    # Retrieve memory context
    from app.core.config import settings as app_settings

    memory_context = ""
    if app_settings.ai_memory_enabled:
        from app.domains.ai.memory import retrieve_relevant_memories
        from app.domains.ai.prompts.memory import format_memory_block

        memories = await retrieve_relevant_memories(
            session, current_user.id, task.title
        )
        memory_context = format_memory_block(memories)

    from app.domains.ai.service import generate_sub_board_questions

    questions = await generate_sub_board_questions(
        task_title=task.title,
        task_description=task.description or "",
        board_title=board.title,
        goal_context=f"{goal_context}\n{qa_pairs}" if goal_context else "",
        language=language,
        user_context=user_context or None,
        memory_context=memory_context or None,
    )

    return SubBoardQuestionsResponse(questions=[q.model_dump() for q in questions])


@tasks_router.post("/{task_id}/generate-sub-board")
async def generate_sub_board_endpoint(
    task_id: str,
    body: SubBoardGenerateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Generate a sub-board for a task using AI (skeleton + enrichment).

    Internally uses the streaming pipeline but returns a standard JSON response.
    """
    import json

    from app.core.config import settings as app_settings
    from app.core.types import BoardSkeletonOutput, TaskEnrichmentOutput
    from app.domains.boards.board_repository import BoardRepository
    from app.domains.boards.dag_utils import (
        CyclicDependencyError,
        GoalNodeValidationError,
        NestingDepthError,
        validate_nesting_depth,
    )
    from app.domains.boards.models import Board
    from app.domains.boards.task_service import (
        auto_start_parent_task,
        create_sub_board_from_skeleton,
        delete_task_subtasks,
        update_task_with_enrichment,
    )

    try:
        task = await validate_task_ownership(session, task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None

    board = await session.get(Board, task.board_id)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        )

    try:
        validate_nesting_depth(board)
    except NestingDepthError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sub-boards cannot be nested. This task belongs to a sub-board.",
        ) from None

    # Check no existing sub-board
    repo = BoardRepository(session)
    existing = await repo.get_sub_board_by_parent_task(task_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sub-board already exists for this task",
        )

    # Check task is not locked (unless already in_progress)
    if task.status == "not_started":
        from app.domains.boards.task_repository import TaskRepository

        task_repo = TaskRepository(session)
        deps_met = await task_repo.are_dependencies_met(task.id)
        if not deps_met:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot create sub-board: task dependencies are not met",
            )

    # Resolve goal context
    goal_id = board.goal_id
    goal = await session.get(Goal, goal_id) if goal_id else None  # type: ignore[arg-type]
    ai_context = dict(goal.ai_context) if goal and goal.ai_context else {}
    classification_data = ai_context.get("classification", {})
    domain = classification_data.get("domain", "general")
    language = classification_data.get("language", "en")
    raw_input = goal.original_input if goal else task.title

    # Format Q&A pairs from answers
    answer_pairs: list[str] = []
    for a in body.answers:
        val = a.value if isinstance(a.value, str) else str(a.value)
        answer_pairs.append(f"Q ({a.question_id}): ?\nA: {val}")
    qa_pairs = "\n\n".join(answer_pairs)

    from app.domains.ai.prompts.meta import format_user_meta_block

    user_context = format_user_meta_block(ai_context.get("user_meta")) or ""

    memory_context = ""
    if app_settings.ai_memory_enabled:
        from app.domains.ai.memory import retrieve_relevant_memories
        from app.domains.ai.prompts.memory import format_memory_block

        memories = await retrieve_relevant_memories(
            session, current_user.id, task.title
        )
        memory_context = format_memory_block(memories)

    # Delete existing subtasks before creating sub-board
    await delete_task_subtasks(session, task)

    # Auto-start parent task
    await auto_start_parent_task(session, task)
    await session.commit()

    # Run the AI pipeline
    from app.domains.ai.service import generate_sub_board_stream

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
        lines = sse_event.strip().split("\n")
        event_type = ""
        event_data: dict = {}
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
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Sub-board skeleton produced invalid graph: {e}",
                ) from None
            except Exception as e:
                logger.error("Sub-board skeleton persistence failed: %s", str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to persist sub-board skeleton",
                ) from None

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

        elif event_type == "generation_error":
            error_msg = event_data.get("message", "Sub-board generation failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

    if sub_board is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sub-board generation produced no output",
        )

    # Return the parent board (refreshed) so the frontend can update the DAG view
    from app.domains.boards.board_service import get_board

    refreshed_board = await get_board(session, board.id, current_user.id)
    user_meta = await get_user_meta_for_board(session, refreshed_board)
    return build_board_response(refreshed_board, user_meta=user_meta)


# ── Artifact Endpoints ───────────────────────────────────


@tasks_router.get("/{task_id}/artifacts", response_model=ArtifactListResponse)
async def list_artifacts_endpoint(
    task_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArtifactListResponse:
    """List all artifacts for a task."""
    try:
        await validate_task_ownership(session, task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None

    artifacts = await list_artifacts(session, task_id)
    return ArtifactListResponse(
        artifacts=[ArtifactResponse.model_validate(a) for a in artifacts]
    )


@tasks_router.get("/{task_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact_endpoint(
    task_id: str,
    artifact_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArtifactResponse:
    """Get a single artifact."""
    try:
        await validate_task_ownership(session, task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None

    try:
        artifact = await validate_artifact_ownership(
            session, artifact_id, current_user.id
        )
    except ArtifactNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        ) from None

    return ArtifactResponse.model_validate(artifact)


@tasks_router.delete(
    "/{task_id}/artifacts/{artifact_id}",
    status_code=204,
    response_model=None,
)
async def delete_artifact_endpoint(
    task_id: str,
    artifact_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete an artifact."""
    try:
        await validate_task_ownership(session, task_id, current_user.id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None

    try:
        await validate_artifact_ownership(session, artifact_id, current_user.id)
    except ArtifactNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        ) from None

    await delete_artifact(session, artifact_id)


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

    Internally uses the streaming skeleton->enrichment pipeline but returns
    a standard JSON response with the fully-built board.
    """
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

    # Delegate to service layer for full orchestration
    try:
        board = await generate_board(session, goal, current_user.id)
    except BoardGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None

    board_user_meta = await get_user_meta_for_board(session, board)
    return build_board_response(board, user_meta=board_user_meta)
