"""Integration tests for board list endpoint (DAG-based)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.goals.models import Goal
from tests.conftest import create_test_board


@pytest.mark.asyncio
async def test_list_boards_empty(
    auth_client: AsyncClient,
) -> None:
    """GET /api/boards returns empty list when no boards exist."""
    response = await auth_client.get("/api/boards")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_boards_with_board(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """GET /api/boards returns boards with summary stats (no column_count)."""
    await create_test_board(session, answered_goal)

    response = await auth_client.get("/api/boards")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    board = data[0]
    assert board["title"] == "Test Board"
    # No column_count — DAG boards don't have columns
    assert "column_count" not in board
    assert board["task_count"] == 3
    # All tasks start as not_started, so completed_task_count = 0
    assert board["completed_task_count"] == 0
    assert "goal_title" in board


@pytest.mark.asyncio
async def test_list_boards_unauthenticated(
    client: AsyncClient,
) -> None:
    """Unauthenticated request returns 401."""
    response = await client.get("/api/boards")
    assert response.status_code == 401
