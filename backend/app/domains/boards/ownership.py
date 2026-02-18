"""Ownership validation helpers for boards, tasks, and subtasks.

Each function loads the entity, walks the ownership chain
(subtask -> task -> board -> goal -> user), and raises a domain
error if the requesting user does not own the resource.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Board, Subtask, Task
from app.domains.goals.models import Goal

# ── Error classes (imported from service for now; will move in Phase 3) ──


class BoardNotFoundError(Exception):
    """Raised when a board is not found or not owned by the user."""


class TaskNotFoundError(Exception):
    """Raised when a task is not found or not owned by the user."""


class SubtaskNotFoundError(Exception):
    """Raised when a subtask is not found or not owned by the user."""


# ── Validation functions ─────────────────────────────────


async def validate_board_ownership(
    session: AsyncSession, board_id: str, user_id: str
) -> Board:
    """Return board if it belongs to user, else raise BoardNotFoundError."""
    board = await session.get(Board, board_id)
    if board is None:
        raise BoardNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError
    return board


async def validate_task_ownership(
    session: AsyncSession, task_id: str, user_id: str
) -> Task:
    """Return task if it belongs to user, else raise TaskNotFoundError."""
    task = await session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError
    board = await session.get(Board, task.board_id)
    if board is None:
        raise TaskNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise TaskNotFoundError
    return task


async def validate_subtask_ownership(
    session: AsyncSession, subtask_id: str, user_id: str
) -> Subtask:
    """Return subtask if it belongs to user, else raise SubtaskNotFoundError."""
    subtask = await session.get(Subtask, subtask_id)
    if subtask is None:
        raise SubtaskNotFoundError
    task = await session.get(Task, subtask.task_id)
    if task is None:
        raise SubtaskNotFoundError
    board = await session.get(Board, task.board_id)
    if board is None:
        raise SubtaskNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise SubtaskNotFoundError
    return subtask


__all__ = [
    "BoardNotFoundError",
    "SubtaskNotFoundError",
    "TaskNotFoundError",
    "validate_board_ownership",
    "validate_subtask_ownership",
    "validate_task_ownership",
]
