"""Business logic for user-facing memory management."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.memory import generate_embedding
from app.domains.ai.memory_repository import MemoryRepository
from app.domains.ai.models import Memory

logger = logging.getLogger(__name__)


class MemoryNotFoundError(Exception):
    """Raised when a memory is not found or not owned by the user."""


async def list_memories(
    session: AsyncSession,
    user_id: str,
    *,
    category: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Memory], int]:
    """List user memories with optional category filter and semantic search.

    If `q` is provided, performs semantic search instead of simple listing.
    """
    if q:
        return await _semantic_search(
            session, user_id, q, category=category, page=page, page_size=page_size
        )

    repo = MemoryRepository(session)
    return await repo.list_memories(
        user_id, category=category, page=page, page_size=page_size
    )


async def _semantic_search(
    session: AsyncSession,
    user_id: str,
    query: str,
    *,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Memory], int]:
    """Semantic search memories using embeddings."""
    from sqlalchemy import text

    query_embedding = await generate_embedding(query)
    if query_embedding is None:
        # Fallback to regular listing if embedding fails
        repo = MemoryRepository(session)
        return await repo.list_memories(
            user_id, category=category, page=page, page_size=page_size
        )

    # Build base query with semantic ordering
    base_where = "user_id = :user_id AND is_archived = false AND embedding IS NOT NULL"
    params: dict[str, object] = {
        "user_id": user_id,
        "embedding": str(query_embedding),
    }
    if category:
        base_where += " AND category = :category"
        params["category"] = category

    # Count
    count_sql = text(f"SELECT COUNT(*) FROM memory WHERE {base_where}")
    count_result = await session.execute(count_sql, params)
    total = count_result.scalar_one()

    # Paginated semantic search
    offset = (page - 1) * page_size
    search_sql = text(
        f"""
        SELECT id FROM memory
        WHERE {base_where}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit OFFSET :offset
        """
    )
    search_params = {**params, "limit": page_size, "offset": offset}
    result = await session.execute(search_sql, search_params)
    rows = result.all()

    memories: list[Memory] = []
    for row in rows:
        mem = await session.get(Memory, row[0])
        if mem is not None:
            memories.append(mem)

    return memories, total


async def get_memory(
    session: AsyncSession,
    memory_id: str,
    user_id: str,
) -> Memory:
    """Get a single memory by ID."""
    repo = MemoryRepository(session)
    memory = await repo.get_by_id(memory_id, user_id)
    if memory is None:
        raise MemoryNotFoundError
    return memory


async def update_memory(
    session: AsyncSession,
    memory_id: str,
    user_id: str,
    content: str,
) -> Memory:
    """Update a memory's content and re-generate its embedding."""
    repo = MemoryRepository(session)
    memory = await repo.get_by_id(memory_id, user_id)
    if memory is None:
        raise MemoryNotFoundError

    # Update content
    memory = await repo.update_content(memory, content)

    # Re-embed (best-effort)
    try:
        new_embedding = await generate_embedding(content)
        if new_embedding is not None:
            memory.embedding = new_embedding
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
    except Exception:
        logger.exception("Re-embedding failed for memory %s", memory_id)

    return memory


async def delete_memory(
    session: AsyncSession,
    memory_id: str,
    user_id: str,
) -> None:
    """Soft-delete a single memory."""
    repo = MemoryRepository(session)
    memory = await repo.get_by_id(memory_id, user_id)
    if memory is None:
        raise MemoryNotFoundError
    await repo.soft_delete(memory)


async def bulk_delete_memories(
    session: AsyncSession,
    user_id: str,
    *,
    category: str | None = None,
) -> int:
    """Bulk soft-delete memories. Returns count of deleted."""
    repo = MemoryRepository(session)
    return await repo.bulk_soft_delete(user_id, category=category)


async def get_memory_stats(
    session: AsyncSession,
    user_id: str,
) -> dict[str, int]:
    """Get memory statistics for a user."""
    repo = MemoryRepository(session)
    return await repo.get_stats(user_id)
