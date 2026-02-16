"""Integration tests for column CRUD endpoints."""

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
                        title="Task 1",
                        description="Do thing 1",
                        position=0,
                    ),
                    BoardGenerationTaskOutput(
                        title="Task 2",
                        description="Do thing 2",
                        position=1,
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="In Progress",
                description="Working on",
                position=1,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Task 3",
                        description="Do thing 3",
                        position=0,
                    ),
                    BoardGenerationTaskOutput(
                        title="Task 4",
                        description="Do thing 4",
                        position=1,
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="Done",
                description="Completed",
                position=2,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Task 5",
                        description="Do thing 5",
                        position=0,
                    ),
                    BoardGenerationTaskOutput(
                        title="Task 6",
                        description="Do thing 6",
                        position=1,
                    ),
                ],
            ),
        ],
    )


async def _create_board(auth_client: AsyncClient, goal_id: str) -> dict:
    """Helper to create a board via AI generation."""
    with patch("app.domains.boards.service.generate_board_from_context") as mock_ai:
        mock_ai.return_value = _mock_board_output()
        response = await auth_client.post(f"/api/goals/{goal_id}/generate-board")
        assert response.status_code == 201
        return response.json()


@pytest.mark.asyncio
async def test_create_column(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """POST /api/boards/:id/columns creates a new column."""
    board = await _create_board(auth_client, answered_goal.id)

    response = await auth_client.post(
        f"/api/boards/{board['id']}/columns",
        json={"title": "Review", "description": "Review tasks"},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["columns"]) == 4
    # New column should be last
    assert data["columns"][-1]["title"] == "Review"
    assert data["columns"][-1]["description"] == "Review tasks"


@pytest.mark.asyncio
async def test_update_column_title(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """PATCH /api/columns/:id updates column title."""
    board = await _create_board(auth_client, answered_goal.id)
    column_id = board["columns"][0]["id"]

    response = await auth_client.patch(
        f"/api/columns/{column_id}",
        json={"title": "Backlog"},
    )
    assert response.status_code == 200
    data = response.json()
    updated_col = next(c for c in data["columns"] if c["id"] == column_id)
    assert updated_col["title"] == "Backlog"


@pytest.mark.asyncio
async def test_delete_empty_column(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """DELETE /api/columns/:id on empty column succeeds without target."""
    board = await _create_board(auth_client, answered_goal.id)

    # Create an empty column
    response = await auth_client.post(
        f"/api/boards/{board['id']}/columns",
        json={"title": "Empty Col"},
    )
    assert response.status_code == 201
    data = response.json()
    empty_col_id = data["columns"][-1]["id"]

    # Delete the empty column
    response = await auth_client.delete(f"/api/columns/{empty_col_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["columns"]) == 3  # back to original 3


@pytest.mark.asyncio
async def test_delete_column_with_migration(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """DELETE /api/columns/:id with tasks migrates them to target column."""
    board = await _create_board(auth_client, answered_goal.id)
    col_to_delete = board["columns"][0]
    target_col = board["columns"][1]
    original_target_task_count = len(target_col["tasks"])
    tasks_to_move = len(col_to_delete["tasks"])

    response = await auth_client.delete(
        f"/api/columns/{col_to_delete['id']}",
        params={"target_column_id": target_col["id"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["columns"]) == 2  # one column deleted
    # Target column should have its original tasks + migrated tasks
    target = next(c for c in data["columns"] if c["id"] == target_col["id"])
    assert len(target["tasks"]) == original_target_task_count + tasks_to_move


@pytest.mark.asyncio
async def test_delete_column_with_tasks_no_target_returns_409(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """DELETE /api/columns/:id with tasks but no target returns 409."""
    board = await _create_board(auth_client, answered_goal.id)
    col_with_tasks = board["columns"][0]

    response = await auth_client.delete(f"/api/columns/{col_with_tasks['id']}")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_column_not_found(
    auth_client: AsyncClient,
) -> None:
    """Operations on nonexistent column return 404."""
    response = await auth_client.patch(
        "/api/columns/nonexistent",
        json={"title": "Test"},
    )
    assert response.status_code == 404

    response = await auth_client.delete("/api/columns/nonexistent")
    assert response.status_code == 404
