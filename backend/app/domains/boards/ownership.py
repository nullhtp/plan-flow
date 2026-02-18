"""Ownership validation helpers for boards, tasks, and subtasks.

Each function loads the entity, walks the ownership chain
(subtask -> task -> board -> goal -> user), and raises a domain
error if the requesting user does not own the resource.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Artifact, Board, Subtask, Task
from app.domains.goals.models import Goal

# ── Error classes (imported from service for now; will move in Phase 3) ──


class BoardNotFoundError(Exception):
    """Raised when a board is not found or not owned by the user."""


class TaskNotFoundError(Exception):
    """Raised when a task is not found or not owned by the user."""


class SubtaskNotFoundError(Exception):
    """Raised when a subtask is not found or not owned by the user."""


class ArtifactNotFoundError(Exception):
    """Raised when an artifact is not found or not owned by the user."""


# ── Validation functions ─────────────────────────────────


async def _resolve_goal_for_board(session: AsyncSession, board: Board) -> Goal | None:
    """Resolve the owning Goal for a board (root or sub-board).

    Root boards: board.goal_id -> Goal
    Sub-boards: board.parent_task_id -> Task -> Board -> ... -> Goal
    """
    if board.goal_id is not None:
        return await session.get(Goal, board.goal_id)
    if board.parent_task_id is not None:
        parent_task = await session.get(Task, board.parent_task_id)
        if parent_task is None:
            return None
        parent_board = await session.get(Board, parent_task.board_id)
        if parent_board is None:
            return None
        return await _resolve_goal_for_board(session, parent_board)
    return None


async def validate_board_ownership(
    session: AsyncSession, board_id: str, user_id: str
) -> Board:
    """Return board if it belongs to user, else raise BoardNotFoundError.

    Supports both root boards and sub-boards (traces ownership chain).
    """
    board = await session.get(Board, board_id)
    if board is None:
        raise BoardNotFoundError
    goal = await _resolve_goal_for_board(session, board)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError
    return board


async def validate_task_ownership(
    session: AsyncSession, task_id: str, user_id: str
) -> Task:
    """Return task if it belongs to user, else raise TaskNotFoundError.

    Supports tasks on both root boards and sub-boards.
    """
    task = await session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError
    board = await session.get(Board, task.board_id)
    if board is None:
        raise TaskNotFoundError
    goal = await _resolve_goal_for_board(session, board)
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
    goal = await _resolve_goal_for_board(session, board)
    if goal is None or goal.user_id != user_id:
        raise SubtaskNotFoundError
    return subtask


async def validate_artifact_ownership(
    session: AsyncSession, artifact_id: str, user_id: str
) -> Artifact:
    """Return artifact if it belongs to user, else raise ArtifactNotFoundError."""
    artifact = await session.get(Artifact, artifact_id)
    if artifact is None:
        raise ArtifactNotFoundError
    task = await session.get(Task, artifact.task_id)
    if task is None:
        raise ArtifactNotFoundError
    board = await session.get(Board, task.board_id)
    if board is None:
        raise ArtifactNotFoundError
    goal = await _resolve_goal_for_board(session, board)
    if goal is None or goal.user_id != user_id:
        raise ArtifactNotFoundError
    return artifact


__all__ = [
    "ArtifactNotFoundError",
    "BoardNotFoundError",
    "SubtaskNotFoundError",
    "TaskNotFoundError",
    "validate_artifact_ownership",
    "validate_board_ownership",
    "validate_subtask_ownership",
    "validate_task_ownership",
]
