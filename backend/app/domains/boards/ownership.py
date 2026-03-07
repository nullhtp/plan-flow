"""Ownership and access validation helpers for boards, tasks, and subtasks.

Each function loads the entity, walks the ownership chain
(subtask -> task -> board -> goal -> user), and raises a domain
error if the requesting user does not have access.

Owner = goal.user_id (full control).
Collaborator = board_member record
(everything except board deletion / share management).
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.member_repository import MemberRepository
from app.domains.boards.models import Artifact, Board, Subtask, Task
from app.domains.goals.models import Goal

# ── Error classes ────────────────────────────────────────


class BoardNotFoundError(Exception):
    """Raised when a board is not found or not accessible by the user."""


class TaskNotFoundError(Exception):
    """Raised when a task is not found or not accessible by the user."""


class SubtaskNotFoundError(Exception):
    """Raised when a subtask is not found or not accessible by the user."""


class ArtifactNotFoundError(Exception):
    """Raised when an artifact is not found or not accessible by the user."""


class AccessDeniedError(Exception):
    """Raised when a collaborator attempts an owner-only action."""


# ── Internal helpers ─────────────────────────────────────


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


async def _resolve_root_board(session: AsyncSession, board: Board) -> Board:
    """Walk up the sub-board chain to find the root board."""
    if board.goal_id is not None:
        return board
    if board.parent_task_id is not None:
        parent_task = await session.get(Task, board.parent_task_id)
        if parent_task is None:
            return board
        parent_board = await session.get(Board, parent_task.board_id)
        if parent_board is None:
            return board
        return await _resolve_root_board(session, parent_board)
    return board


async def get_user_role_for_board(
    session: AsyncSession, board_id: str, user_id: str
) -> Literal["owner", "collaborator"] | None:
    """Determine the user's role for a board, or None if no access.

    Checks ownership via goal.user_id first, then membership on the root board.
    """
    board = await session.get(Board, board_id)
    if board is None:
        return None

    goal = await _resolve_goal_for_board(session, board)
    if goal is not None and goal.user_id == user_id:
        return "owner"

    # Check membership on the root board
    root_board = await _resolve_root_board(session, board)
    repo = MemberRepository(session)
    if await repo.is_member(root_board.id, user_id):
        return "collaborator"

    return None


# ── Validation functions ─────────────────────────────────


async def validate_board_ownership(
    session: AsyncSession, board_id: str, user_id: str
) -> Board:
    """Return board if user is the OWNER, else raise BoardNotFoundError.

    Use this for owner-only actions (board deletion, share management).
    """
    board = await session.get(Board, board_id)
    if board is None:
        raise BoardNotFoundError
    goal = await _resolve_goal_for_board(session, board)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError
    return board


async def validate_board_access(
    session: AsyncSession, board_id: str, user_id: str
) -> Board:
    """Return board if user is owner OR collaborator, else raise BoardNotFoundError.

    Use this for general access (viewing, editing tasks, etc.).
    """
    board = await session.get(Board, board_id)
    if board is None:
        raise BoardNotFoundError

    role = await get_user_role_for_board(session, board_id, user_id)
    if role is None:
        raise BoardNotFoundError
    return board


async def validate_task_ownership(
    session: AsyncSession, task_id: str, user_id: str
) -> Task:
    """Return task if user has access, else raise TaskNotFoundError."""
    task = await session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError
    board = await session.get(Board, task.board_id)
    if board is None:
        raise TaskNotFoundError

    role = await get_user_role_for_board(session, board.id, user_id)
    if role is None:
        raise TaskNotFoundError
    return task


async def validate_subtask_ownership(
    session: AsyncSession, subtask_id: str, user_id: str
) -> Subtask:
    """Return subtask if user has access, else raise SubtaskNotFoundError."""
    subtask = await session.get(Subtask, subtask_id)
    if subtask is None:
        raise SubtaskNotFoundError
    task = await session.get(Task, subtask.task_id)
    if task is None:
        raise SubtaskNotFoundError
    board = await session.get(Board, task.board_id)
    if board is None:
        raise SubtaskNotFoundError

    role = await get_user_role_for_board(session, board.id, user_id)
    if role is None:
        raise SubtaskNotFoundError
    return subtask


async def validate_artifact_ownership(
    session: AsyncSession, artifact_id: str, user_id: str
) -> Artifact:
    """Return artifact if user has access, else raise ArtifactNotFoundError."""
    artifact = await session.get(Artifact, artifact_id)
    if artifact is None:
        raise ArtifactNotFoundError
    task = await session.get(Task, artifact.task_id)
    if task is None:
        raise ArtifactNotFoundError
    board = await session.get(Board, task.board_id)
    if board is None:
        raise ArtifactNotFoundError

    role = await get_user_role_for_board(session, board.id, user_id)
    if role is None:
        raise ArtifactNotFoundError
    return artifact


__all__ = [
    "AccessDeniedError",
    "ArtifactNotFoundError",
    "BoardNotFoundError",
    "SubtaskNotFoundError",
    "TaskNotFoundError",
    "get_user_role_for_board",
    "validate_artifact_ownership",
    "validate_board_access",
    "validate_board_ownership",
    "validate_subtask_ownership",
    "validate_task_ownership",
]
