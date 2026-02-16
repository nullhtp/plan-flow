from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
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
    create_subtask,
    create_task,
    delete_subtask,
    delete_task,
    generate_board_for_goal,
    get_board,
    list_boards,
    update_board,
    update_subtask,
    update_task,
)

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

    return _build_board_response(board)


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
    """Generate a board for a goal using AI. The goal must be in 'answered' status."""
    from app.domains.ai.service import AIOutputError

    try:
        board = await generate_board_for_goal(session, goal_id, current_user.id)
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
    except AIOutputError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing failed. Please try again.",
        ) from None

    return _build_board_response(board)
