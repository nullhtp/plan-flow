"""Integration tests for board list endpoint (DAG-based)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.domains.ai.schemas import (
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)
from app.domains.goals.models import Goal


def _mock_board_output() -> BoardGenerationOutput:
    return BoardGenerationOutput(
        board_title="Test Board",
        tasks=[
            BoardGenerationTaskOutput(
                id="t1",
                title="Task 1",
                description="Do thing 1",
                depends_on=[],
                is_goal_node=False,
            ),
            BoardGenerationTaskOutput(
                id="t2",
                title="Task 2",
                description="Do thing 2",
                depends_on=[],
                is_goal_node=False,
            ),
            BoardGenerationTaskOutput(
                id="t3",
                title="Task 3",
                description="Do thing 3",
                depends_on=["t1", "t2"],
                is_goal_node=True,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_list_boards_empty(
    auth_client: AsyncClient,
) -> None:
    """GET /api/boards returns empty list when no boards exist."""
    response = await auth_client.get("/api/boards")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_list_boards_with_board(
    mock_ai,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """GET /api/boards returns boards with summary stats (no column_count)."""
    mock_ai.return_value = _mock_board_output()

    # Create a board
    await auth_client.post(f"/api/goals/{answered_goal.id}/generate-board")

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
