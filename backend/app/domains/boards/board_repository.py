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
        """Fetch a board with tasks, subtasks, and dependency edges eager-loaded."""
        self.session.expire_all()
        stmt = (
            select(Board)
            .options(
                selectinload(Board.tasks).selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependencies),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependents),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
            .where(Board.id == board_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_relations_by_goal(self, goal_id: str) -> Board | None:
        """Fetch a board by goal_id with all relations eager-loaded."""
        self.session.expire_all()
        stmt = (
            select(Board)
            .options(
                selectinload(Board.tasks).selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependencies),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(Board.tasks).selectinload(Task.dependents),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
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

    async def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Return all boards for a user with summary stats.

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
            .where(Goal.user_id == user_id)
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


__all__ = ["BoardRepository"]
