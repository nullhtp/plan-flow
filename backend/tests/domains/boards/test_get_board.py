"""Integration tests for GET board endpoint (DAG-based)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.goals.models import Goal
from tests.conftest import create_test_board, make_skeleton


@pytest.mark.asyncio
async def test_get_board_success(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """GET board returns DAG structure with tasks and edges."""
    skeleton = make_skeleton(
        board_title="Relocate from Berlin to Lisbon",
        tasks=[
            {
                "id": "t1",
                "title": "Research visa",
                "depends_on": [],
                "is_goal_node": False,
            },
            {
                "id": "t2",
                "title": "Research areas",
                "depends_on": [],
                "is_goal_node": False,
            },
            {
                "id": "t3",
                "title": "Gather docs",
                "depends_on": ["t1"],
                "is_goal_node": False,
            },
            {
                "id": "t4",
                "title": "Apply visa",
                "depends_on": ["t3"],
                "is_goal_node": False,
            },
            {
                "id": "t5",
                "title": "Book flight",
                "depends_on": ["t4", "t2"],
                "is_goal_node": True,
            },
        ],
    )
    board, _ = await create_test_board(session, answered_goal, skeleton)

    response = await auth_client.get(f"/api/boards/{board.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == board.id
    assert data["goal_id"] == answered_goal.id
    assert data["title"] == "Relocate from Berlin to Lisbon"
    # DAG structure: flat task list, not columns
    assert "tasks" in data
    assert len(data["tasks"]) == 5
    assert "columns" not in data
    # Check edges
    assert "edges" in data
    assert len(data["edges"]) >= 4
    # Check task fields
    task = next(t for t in data["tasks"] if t["title"] == "Research visa")
    assert task["status"] == "not_started"
    assert task["is_goal_node"] is False
    assert task["is_locked"] is False  # no deps
    assert task["dependency_ids"] == []
    # Check goal node
    goal_task = next(t for t in data["tasks"] if t["is_goal_node"])
    assert goal_task["title"] == "Book flight"
    assert goal_task["is_locked"] is True  # has unmet deps
    assert len(goal_task["dependency_ids"]) == 2
    # is_completed should be false
    assert data["is_completed"] is False


@pytest.mark.asyncio
async def test_get_board_not_found(
    auth_client: AsyncClient,
) -> None:
    """Non-existent board returns 404."""
    response = await auth_client.get("/api/boards/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_board_unauthenticated(
    client: AsyncClient,
) -> None:
    """Unauthenticated request returns 401."""
    response = await client.get("/api/boards/some-id")
    assert response.status_code == 401
