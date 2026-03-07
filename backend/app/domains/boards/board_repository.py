"""Data-access layer for boards."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.boards.models import Board, Task
from app.domains.goals.models import Goal


class BoardRepository:
    """Encapsulates all database queries for :class:`Board`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, board_id: str) -> Board | None:
        """Fetch a board by primary key (no relations loaded)."""
        return await self.session.get(Board, board_id)

    async def get_by_goal_id(self, goal_id: str) -> Board | None:
        """Fetch a board by its goal_id (no relations loaded)."""
        stmt = select(Board).where(Board.goal_id == goal_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_relations(self, board_id: str) -> Board | None:
        """Fetch a board with tasks, subtasks, sub-boards, and edges."""
        stmt = (
            select(Board)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Board.tasks).selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependencies),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependents),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks)
                .selectinload(Task.sub_board)
                .selectinload(Board.tasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
            .where(Board.id == board_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_relations_by_goal(self, goal_id: str) -> Board | None:
        """Fetch a board by goal_id with all relations eager-loaded."""
        stmt = (
            select(Board)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Board.tasks).selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependencies),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependents),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks)
                .selectinload(Task.sub_board)
                .selectinload(Board.tasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
            .where(Board.goal_id == goal_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, board: Board) -> Board:
        """Persist a new board (flush only, caller commits)."""
        self.session.add(board)
        await self.session.flush()
        return board

    async def update(self, board: Board) -> None:
        """Mark a board as dirty so changes are flushed on next commit."""
        self.session.add(board)

    async def get_sub_board_by_parent_task(self, task_id: str) -> Board | None:
        """Fetch a sub-board by its parent_task_id."""
        stmt = select(Board).where(Board.parent_task_id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_root_boards_for_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return root boards (no parent_task_id) for a user with stats.

        Each dict contains: id, goal_id, title, goal_title, task_count,
        completed_task_count, created_at.
        """
        stmt = (
            select(
                Board.id,
                Board.goal_id,
                Board.title,
                Board.created_at,
                Goal.title.label("goal_title"),
            )
            .join(Goal, Board.goal_id == Goal.id)
            .where(Goal.user_id == user_id, Board.parent_task_id.is_(None))  # pyright: ignore[reportUnknownMemberType]
            .order_by(Board.created_at.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        boards: list[dict[str, Any]] = []
        for row in rows:
            task_count_stmt = (
                select(func.count()).select_from(Task).where(Task.board_id == row.id)
            )
            task_count_result = await self.session.execute(task_count_stmt)
            task_count = task_count_result.scalar() or 0

            completed_stmt = (
                select(func.count())
                .select_from(Task)
                .where(Task.board_id == row.id, Task.status == "done")
            )
            completed_result = await self.session.execute(completed_stmt)
            completed_count = completed_result.scalar() or 0

            boards.append(
                {
                    "id": row.id,
                    "goal_id": row.goal_id,
                    "title": row.title,
                    "goal_title": row.goal_title,
                    "task_count": task_count,
                    "completed_task_count": completed_count,
                    "created_at": row.created_at,
                }
            )

        return boards

    async def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return all root boards for a user with summary stats.

        Delegates to list_root_boards_for_user (filters to parent_task_id IS NULL).
        """
        return await self.list_root_boards_for_user(user_id)

    async def list_root_boards_by_ids(
        self, board_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Return root boards matching the given IDs with summary stats."""
        if not board_ids:
            return []

        stmt = (
            select(
                Board.id,
                Board.goal_id,
                Board.title,
                Board.created_at,
                Goal.title.label("goal_title"),
            )
            .join(Goal, Board.goal_id == Goal.id)
            .where(
                Board.id.in_(board_ids),
                Board.parent_task_id.is_(None),  # pyright: ignore[reportUnknownMemberType]
            )
            .order_by(Board.created_at.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        boards: list[dict[str, Any]] = []
        for row in rows:
            task_count_stmt = (
                select(func.count()).select_from(Task).where(Task.board_id == row.id)
            )
            task_count_result = await self.session.execute(task_count_stmt)
            task_count = task_count_result.scalar() or 0

            completed_stmt = (
                select(func.count())
                .select_from(Task)
                .where(Task.board_id == row.id, Task.status == "done")
            )
            completed_result = await self.session.execute(completed_stmt)
            completed_count = completed_result.scalar() or 0

            boards.append(
                {
                    "id": row.id,
                    "goal_id": row.goal_id,
                    "title": row.title,
                    "goal_title": row.goal_title,
                    "task_count": task_count,
                    "completed_task_count": completed_count,
                    "created_at": row.created_at,
                }
            )

        return boards

    async def get_parent_board(self, board: Board) -> Board | None:
        """Get the parent board for a sub-board.

        Traces: sub-board -> parent_task -> parent_task's board.
        Returns None for root boards.
        """
        if board.parent_task_id is None:
            return None

        parent_task = await self.session.get(Task, board.parent_task_id)
        if parent_task is None:
            return None

        return await self.get_by_id(parent_task.board_id)


__all__ = ["BoardRepository"]
