"""Memory management API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domains.ai.memory_service import (
    MemoryNotFoundError,
    bulk_delete_memories,
    delete_memory,
    get_memory,
    get_memory_stats,
    list_memories,
    update_memory,
)
from app.domains.ai.schemas import (
    MemoryBulkDeleteRequest,
    MemoryListResponse,
    MemoryResponse,
    MemoryStatsResponse,
    MemoryUpdateRequest,
)
from app.domains.auth.deps import CurrentUser

router = APIRouter(prefix="/memories", tags=["memories"])
boards_memory_router = APIRouter(prefix="/boards", tags=["memories"])


def _memory_to_response(memory: object) -> MemoryResponse:
    """Convert a Memory ORM object to a MemoryResponse."""
    from app.domains.ai.models import Memory

    assert isinstance(memory, Memory)
    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        category=memory.category,
        source_stage=memory.source_stage,
        created_at=memory.created_at.isoformat(),
        last_used_at=memory.last_used_at.isoformat() if memory.last_used_at else None,
    )


@router.get("", response_model=MemoryListResponse)
async def get_memories(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Semantic search query"),
) -> MemoryListResponse:
    """List user memories with optional filtering and semantic search."""
    memories, total = await list_memories(
        session, current_user.id, category=category, q=q, page=page, page_size=page_size
    )
    return MemoryListResponse(
        items=[_memory_to_response(m) for m in memories],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_stats(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MemoryStatsResponse:
    """Get memory statistics for the current user."""
    stats = await get_memory_stats(session, current_user.id)
    total = stats.pop("total", 0)
    return MemoryStatsResponse(total=total, by_category=stats)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory_by_id(
    memory_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MemoryResponse:
    """Get a single memory by ID."""
    try:
        memory = await get_memory(session, memory_id, current_user.id)
    except MemoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
        ) from None
    return _memory_to_response(memory)


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def patch_memory(
    memory_id: str,
    body: MemoryUpdateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MemoryResponse:
    """Update a memory's content (triggers re-embedding)."""
    try:
        memory = await update_memory(session, memory_id, current_user.id, body.content)
    except MemoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
        ) from None
    return _memory_to_response(memory)


@router.delete(
    "/{memory_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_memory_by_id(
    memory_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Soft-delete a single memory."""
    try:
        await delete_memory(session, memory_id, current_user.id)
    except MemoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
        ) from None


@router.delete("", status_code=status.HTTP_200_OK)
async def bulk_delete(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: MemoryBulkDeleteRequest | None = None,
) -> dict[str, int]:
    """Bulk soft-delete memories, optionally filtered by category."""
    category = body.category if body else None
    count = await bulk_delete_memories(session, current_user.id, category=category)
    return {"deleted": count}


# ── Board-contextual memories ────────────────────────────


@boards_memory_router.get("/{board_id}/memories", response_model=list[MemoryResponse])
async def get_board_memories(
    board_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=10, ge=1, le=50),
) -> list[MemoryResponse]:
    """Get memories relevant to a specific board's goal context."""
    from app.domains.boards.models import Board
    from app.domains.boards.ownership import _resolve_goal_for_board

    board = await session.get(Board, board_id)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )

    goal = await _resolve_goal_for_board(session, board)
    if goal is None or goal.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    from app.domains.ai.memory import retrieve_relevant_memories

    query = f"{board.title} {goal.original_input}"
    memories = await retrieve_relevant_memories(
        session, current_user.id, query, limit=limit
    )
    return [_memory_to_response(m) for m in memories]
