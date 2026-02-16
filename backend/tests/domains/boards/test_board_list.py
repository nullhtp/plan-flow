"""Integration tests for board list endpoint."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.domains.ai.schemas import (
    BoardGenerationColumnOutput,
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)
from app.domains.goals.models import Goal


def _mock_board_output() -> BoardGenerationOutput:
    return BoardGenerationOutput(
        board_title="Test Board",
        columns=[
            BoardGenerationColumnOutput(
                title="To Do",
                description="Tasks to do",
                position=0,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Task 1", description="Do thing 1", position=0
                    ),
                    BoardGenerationTaskOutput(
                        title="Task 2", description="Do thing 2", position=1
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="In Progress",
                description="Working on",
                position=1,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Task 3", description="Do thing 3", position=0
                    ),
                    BoardGenerationTaskOutput(
                        title="Task 4", description="Do thing 4", position=1
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="Done",
                description="Completed",
                position=2,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Task 5", description="Do thing 5", position=0
                    ),
                    BoardGenerationTaskOutput(
                        title="Task 6", description="Do thing 6", position=1
                    ),
                ],
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
    """GET /api/boards returns boards with summary stats."""
    mock_ai.return_value = _mock_board_output()

    # Create a board
    await auth_client.post(f"/api/goals/{answered_goal.id}/generate-board")

    response = await auth_client.get("/api/boards")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    board = data[0]
    assert board["title"] == "Test Board"
    assert board["column_count"] == 3
    assert board["task_count"] == 6
    # completed_task_count = tasks in last column (Done)
    assert board["completed_task_count"] == 2
    assert "goal_title" in board


@pytest.mark.asyncio
async def test_list_boards_unauthenticated(
    client: AsyncClient,
) -> None:
    """Unauthenticated request returns 401."""
    response = await client.get("/api/boards")
    assert response.status_code == 401
