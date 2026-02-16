"""Integration tests for board generation endpoint (DAG-based)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.domains.ai.schemas import (
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)
from app.domains.ai.service import AIOutputError
from app.domains.goals.models import Goal


def _mock_board_output() -> BoardGenerationOutput:
    """Create a mock DAG board output with a diamond-shaped dependency graph."""
    return BoardGenerationOutput(
        board_title="Relocate from Berlin to Lisbon",
        tasks=[
            BoardGenerationTaskOutput(
                id="t1",
                title="Research visa requirements",
                description="Check D7 visa and NHR options",
                depends_on=[],
                is_goal_node=False,
                priority="high",
                estimated_minutes=60,
            ),
            BoardGenerationTaskOutput(
                id="t2",
                title="Research neighborhoods",
                description="Find suitable areas in Lisbon",
                depends_on=[],
                is_goal_node=False,
                estimated_minutes=90,
            ),
            BoardGenerationTaskOutput(
                id="t3",
                title="Gather documents",
                description="Collect passport, bank statements, etc.",
                depends_on=["t1"],
                is_goal_node=False,
                priority="high",
            ),
            BoardGenerationTaskOutput(
                id="t4",
                title="Apply for visa",
                description="Submit D7 visa application",
                depends_on=["t3"],
                is_goal_node=False,
                due_date="2026-03-15",
                priority="high",
                estimated_minutes=120,
            ),
            BoardGenerationTaskOutput(
                id="t5",
                title="Book flight",
                description="Book one-way flight to Lisbon",
                depends_on=["t4", "t2"],
                is_goal_node=True,
                due_date="2026-04-01",
                priority="medium",
                estimated_minutes=30,
            ),
        ],
    )


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_success(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Successful board generation returns 201 with DAG board data."""
    mock_ai.return_value = _mock_board_output()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["goal_id"] == answered_goal.id
    assert data["title"] == "Relocate from Berlin to Lisbon"
    # Flat task list (not columns)
    assert "tasks" in data
    assert len(data["tasks"]) == 5
    assert "columns" not in data
    # Check edges
    assert "edges" in data
    assert len(data["edges"]) > 0
    # Check first task
    task_titles = {t["title"] for t in data["tasks"]}
    assert "Research visa requirements" in task_titles
    assert "Book flight" in task_titles
    # Check goal node
    goal_tasks = [t for t in data["tasks"] if t["is_goal_node"]]
    assert len(goal_tasks) == 1
    assert goal_tasks[0]["title"] == "Book flight"
    # Check is_completed is false initially
    assert data["is_completed"] is False
    # Check is_locked: root tasks (no deps) should not be locked
    root_tasks = [t for t in data["tasks"] if t["dependency_ids"] == []]
    for t in root_tasks:
        assert t["is_locked"] is False
    # Check locked: tasks with unmet deps should be locked
    dependent_tasks = [t for t in data["tasks"] if len(t["dependency_ids"]) > 0]
    for t in dependent_tasks:
        assert t["is_locked"] is True


@pytest.mark.asyncio
async def test_generate_board_wrong_status(
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Goal in 'questioning' status returns 409."""
    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/generate-board",
    )
    assert response.status_code == 409
    assert "answered" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_already_exists(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Second generation attempt returns 409."""
    mock_ai.return_value = _mock_board_output()

    # First generation succeeds
    response1 = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response1.status_code == 201

    # Second attempt fails — goal is now 'active', so the status guard triggers first
    response2 = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_generate_board_not_found(
    auth_client: AsyncClient,
) -> None:
    """Non-existent goal returns 404."""
    response = await auth_client.post(
        "/api/goals/nonexistent-id/generate-board",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_board_unauthenticated(
    client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Unauthenticated request returns 401."""
    response = await client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_ai_error_reverts_status(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncMock,
) -> None:
    """AI failure returns 503 and goal status reverts to 'answered'."""
    mock_ai.side_effect = AIOutputError("AI failed")

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 503


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_status_transitions(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Goal transitions from 'answered' to 'active' after board generation."""
    mock_ai.return_value = _mock_board_output()

    # Generate board
    await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )

    # Check goal status is now active
    goal_response = await auth_client.get(f"/api/goals/{answered_goal.id}")
    assert goal_response.status_code == 200
    assert goal_response.json()["status"] == "active"


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_has_edges(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Generated board includes dependency edges in source/target format."""
    mock_ai.return_value = _mock_board_output()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 201
    data = response.json()

    edges = data["edges"]
    assert len(edges) >= 4  # t1->t3, t3->t4, t4->t5, t2->t5
    for edge in edges:
        assert "source" in edge
        assert "target" in edge

    # Verify edges reference valid task IDs
    task_ids = {t["id"] for t in data["tasks"]}
    for edge in edges:
        assert edge["source"] in task_ids
        assert edge["target"] in task_ids
