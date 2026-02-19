"""Integration tests for memory management API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import Memory
from app.domains.auth.models import User


async def _create_memory(
    session: AsyncSession,
    user: User,
    content: str = "User prefers dark mode",
    category: str = "preference",
    source_stage: str = "classification",
) -> Memory:
    """Helper to create a test memory directly in the DB."""
    memory = Memory(
        user_id=user.id,
        content=content,
        category=category,
        source_stage=source_stage,
    )
    session.add(memory)
    await session.commit()
    await session.refresh(memory)
    return memory


@pytest.mark.asyncio
async def test_list_memories_empty(auth_client: AsyncClient) -> None:
    """GET /api/memories returns empty list when no memories exist."""
    response = await auth_client.get("/api/memories")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_memories_with_data(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """GET /api/memories returns user memories."""
    await _create_memory(session, test_user, "Prefers dark mode")
    await _create_memory(session, test_user, "Lives in Berlin", "fact")

    response = await auth_client.get("/api/memories")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_memories_category_filter(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """GET /api/memories?category=fact filters by category."""
    await _create_memory(session, test_user, "Prefers dark mode", "preference")
    await _create_memory(session, test_user, "Lives in Berlin", "fact")

    response = await auth_client.get("/api/memories?category=fact")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "fact"


@pytest.mark.asyncio
async def test_get_memory_by_id(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """GET /api/memories/:id returns a single memory."""
    memory = await _create_memory(session, test_user)

    response = await auth_client.get(f"/api/memories/{memory.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == memory.id
    assert data["content"] == "User prefers dark mode"


@pytest.mark.asyncio
async def test_get_memory_not_found(auth_client: AsyncClient) -> None:
    """GET /api/memories/:id returns 404 for non-existent memory."""
    response = await auth_client.get("/api/memories/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_memory(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """PATCH /api/memories/:id updates content."""
    memory = await _create_memory(session, test_user)

    response = await auth_client.patch(
        f"/api/memories/{memory.id}",
        json={"content": "Updated content"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Updated content"
    assert data["id"] == memory.id


@pytest.mark.asyncio
async def test_delete_memory(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """DELETE /api/memories/:id soft-deletes a memory."""
    memory = await _create_memory(session, test_user)

    response = await auth_client.delete(f"/api/memories/{memory.id}")
    assert response.status_code == 204

    # Should no longer appear in list
    response = await auth_client.get("/api/memories")
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_bulk_delete_all(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """DELETE /api/memories bulk-deletes all memories."""
    await _create_memory(session, test_user, "Memory 1")
    await _create_memory(session, test_user, "Memory 2")

    response = await auth_client.request(
        "DELETE", "/api/memories", json={"category": None}
    )
    assert response.status_code == 200
    assert response.json()["deleted"] == 2

    # All gone
    response = await auth_client.get("/api/memories")
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_bulk_delete_by_category(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """DELETE /api/memories with category only deletes that category."""
    await _create_memory(session, test_user, "Pref 1", "preference")
    await _create_memory(session, test_user, "Fact 1", "fact")

    response = await auth_client.request(
        "DELETE", "/api/memories", json={"category": "preference"}
    )
    assert response.status_code == 200
    assert response.json()["deleted"] == 1

    # Only the fact should remain
    response = await auth_client.get("/api/memories")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "fact"


@pytest.mark.asyncio
async def test_memory_stats(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """GET /api/memories/stats returns correct counts."""
    await _create_memory(session, test_user, "Pref 1", "preference")
    await _create_memory(session, test_user, "Pref 2", "preference")
    await _create_memory(session, test_user, "Fact 1", "fact")

    response = await auth_client.get("/api/memories/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["by_category"]["preference"] == 2
    assert data["by_category"]["fact"] == 1


@pytest.mark.asyncio
async def test_archived_memories_hidden(
    auth_client: AsyncClient, session: AsyncSession, test_user: User
) -> None:
    """Archived memories should not appear in list or stats."""
    mem = await _create_memory(session, test_user, "Active memory")
    archived = Memory(
        user_id=test_user.id,
        content="Archived memory",
        category="fact",
        source_stage="classification",
        is_archived=True,
    )
    session.add(archived)
    await session.commit()

    # List should only show active
    response = await auth_client.get("/api/memories")
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == mem.id

    # Stats should only count active
    response = await auth_client.get("/api/memories/stats")
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_memories_require_auth(client: AsyncClient) -> None:
    """Memory endpoints require authentication."""
    response = await client.get("/api/memories")
    assert response.status_code == 401

    response = await client.get("/api/memories/stats")
    assert response.status_code == 401
