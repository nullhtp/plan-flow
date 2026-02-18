"""Data-access layer for subtasks."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Subtask


class SubtaskRepository:
    """Encapsulates all database queries for :class:`Subtask`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, subtask_id: str) -> Subtask | None:
        """Fetch a subtask by primary key."""
        return await self.session.get(Subtask, subtask_id)

    async def create(self, subtask: Subtask) -> Subtask:
        """Persist a new subtask (flush only, caller commits)."""
        self.session.add(subtask)
        await self.session.flush()
        return subtask

    async def update(self, subtask: Subtask) -> None:
        """Mark a subtask as dirty so changes are flushed on next commit."""
        self.session.add(subtask)

    async def delete(self, subtask: Subtask) -> None:
        """Remove a subtask from the database."""
        await self.session.delete(subtask)

    async def get_last_position(self, task_id: str) -> str | None:
        """Return the highest position key for subtasks of a task, or None."""
        stmt = (
            select(Subtask.position)
            .where(Subtask.task_id == task_id)
            .order_by(Subtask.position.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar()


__all__ = ["SubtaskRepository"]
