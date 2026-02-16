"""Integration tests for GET board endpoint (DAG-based)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.domains.ai.schemas import (
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)
from app.domains.goals.models import Goal


def _mock_board_output() -> BoardGenerationOutput:
    return BoardGenerationOutput(
        board_title="Relocate from Berlin to Lisbon",
        tasks=[
            BoardGenerationTaskOutput(
                id="t1",
                title="Research visa",
                description="Check visa options",
                depends_on=[],
                is_goal_node=False,
                priority="high",
            ),
            BoardGenerationTaskOutput(
                id="t2",
                title="Research areas",
                description="Find neighborhoods",
                depends_on=[],
                is_goal_node=False,
            ),
            BoardGenerationTaskOutput(
                id="t3",
                title="Gather docs",
                description="Collect paperwork",
                depends_on=["t1"],
                is_goal_node=False,
            ),
            BoardGenerationTaskOutput(
                id="t4",
                title="Apply visa",
                description="Submit application",
                depends_on=["t3"],
                is_goal_node=False,
                due_date="2026-03-15",
            ),
            BoardGenerationTaskOutput(
                id="t5",
                title="Book flight",
                description="Book ticket",
                depends_on=["t4", "t2"],
                is_goal_node=True,
                estimated_minutes=30,
            ),
        ],
    )


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_get_board_success(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """GET board returns DAG structure with tasks and edges."""
    mock_ai.return_value = _mock_board_output()

    # Create board first
    create_response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert create_response.status_code == 201
    board_id = create_response.json()["id"]

    # Retrieve board
    response = await auth_client.get(f"/api/boards/{board_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == board_id
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
    assert task["priority"] == "high"
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
