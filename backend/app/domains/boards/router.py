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
    return build_board_response(board, user_meta=user_meta)


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
