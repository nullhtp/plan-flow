"""Data-access layer for memory management CRUD operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import Memory


class MemoryRepository:
    """Encapsulates database queries for user-facing memory management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_memories(
        self,
        user_id: str,
        *,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Memory], int]:
        """List active (non-archived) memories with pagination.

        Returns (memories, total_count).
        """
        base = select(Memory).where(
            Memory.user_id == user_id,
            Memory.is_archived == False,  # noqa: E712
        )
        if category:
            base = base.where(Memory.category == category)

        # Count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Paginated results
        stmt = (
            base.order_by(Memory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )  # type: ignore[union-attr]
        result = await self.session.execute(stmt)
        memories = list(result.scalars().all())

        return memories, total

    async def get_by_id(self, memory_id: str, user_id: str) -> Memory | None:
        """Get a single active memory by ID, verifying ownership."""
        memory = await self.session.get(Memory, memory_id)
        if memory is None or memory.user_id != user_id or memory.is_archived:
            return None
        return memory

    async def update_content(self, memory: Memory, content: str) -> Memory:
        """Update a memory's content (caller handles re-embedding)."""
        memory.content = content
        memory.last_used_at = datetime.now(UTC)
        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)
        return memory

    async def soft_delete(self, memory: Memory) -> None:
        """Soft-delete a memory by setting is_archived = True."""
        memory.is_archived = True
        self.session.add(memory)
        await self.session.commit()

    async def bulk_soft_delete(
        self, user_id: str, *, category: str | None = None
    ) -> int:
        """Bulk soft-delete all active memories, optionally filtered by category.

        Returns the number of archived memories.
        """
        stmt = (
            update(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.is_archived == False,  # noqa: E712
            )
            .values(is_archived=True)
        )
        if category:
            stmt = stmt.where(Memory.category == category)

        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount  # type: ignore[return-value]

    async def get_stats(self, user_id: str) -> dict[str, int]:
        """Get memory count stats grouped by category.

        Returns dict with 'total' and per-category counts.
        """
        stmt = (
            select(Memory.category, func.count().label("cnt"))
            .where(
                Memory.user_id == user_id,
                Memory.is_archived == False,  # noqa: E712
            )
            .group_by(Memory.category)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        by_category: dict[str, int] = {}
        total = 0
        for cat, cnt in rows:
            by_category[cat] = cnt
            total += cnt

        return {"total": total, **by_category}


__all__ = ["MemoryRepository"]
