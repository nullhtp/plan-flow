from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domains.auth.deps import CurrentUser
from app.domains.boards.schemas import BoardResponse
from app.domains.boards.service import (
    BoardAlreadyExistsError,
    BoardNotFoundError,
    GoalNotReadyError,
    generate_board_for_goal,
    get_board,
)

# Router for board CRUD endpoints (/api/boards/...)
router = APIRouter(prefix="/boards", tags=["boards"])

# Router for goal-scoped board endpoints (/api/goals/:id/generate-board)
goals_router = APIRouter(prefix="/goals", tags=["boards"])


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

    return BoardResponse.model_validate(board)


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board_endpoint(
    board_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BoardResponse:
    """Get a board by ID with nested columns and tasks."""
    try:
        board = await get_board(session, board_id, current_user.id)
    except BoardNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        ) from None

    return BoardResponse.model_validate(board)
