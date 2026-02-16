"""Integration tests for task CRUD endpoints."""

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


async def _create_board(auth_client: AsyncClient, goal_id: str) -> dict:
    with patch("app.domains.boards.service.generate_board_from_context") as mock_ai:
        mock_ai.return_value = _mock_board_output()
        response = await auth_client.post(f"/api/goals/{goal_id}/generate-board")
        assert response.status_code == 201
        return response.json()


@pytest.mark.asyncio
async def test_create_task(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """POST /api/columns/:id/tasks creates a new task."""
    board = await _create_board(auth_client, answered_goal.id)
    column_id = board["columns"][0]["id"]
    original_count = len(board["columns"][0]["tasks"])

    response = await auth_client.post(
        f"/api/columns/{column_id}/tasks",
        json={
            "title": "New Task",
            "description": "A new task",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    data = response.json()
    col = next(c for c in data["columns"] if c["id"] == column_id)
    assert len(col["tasks"]) == original_count + 1
    assert col["tasks"][-1]["title"] == "New Task"
    assert col["tasks"][-1]["priority"] == "high"


@pytest.mark.asyncio
async def test_update_task_title(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """PATCH /api/tasks/:id updates task title."""
    board = await _create_board(auth_client, answered_goal.id)
    task_id = board["columns"][0]["tasks"][0]["id"]

    response = await auth_client.patch(
        f"/api/tasks/{task_id}",
        json={"title": "Updated Title"},
    )
    assert response.status_code == 200
    data = response.json()
    task = next(t for c in data["columns"] for t in c["tasks"] if t["id"] == task_id)
    assert task["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_move_task_to_another_column(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """PATCH /api/tasks/:id with column_id moves task between columns."""
    board = await _create_board(auth_client, answered_goal.id)
    source_col = board["columns"][0]
    target_col = board["columns"][1]
    task_id = source_col["tasks"][0]["id"]
    original_source_count = len(source_col["tasks"])
    original_target_count = len(target_col["tasks"])

    response = await auth_client.patch(
        f"/api/tasks/{task_id}",
        json={"column_id": target_col["id"]},
    )
    assert response.status_code == 200
    data = response.json()
    source = next(c for c in data["columns"] if c["id"] == source_col["id"])
    target = next(c for c in data["columns"] if c["id"] == target_col["id"])
    assert len(source["tasks"]) == original_source_count - 1
    assert len(target["tasks"]) == original_target_count + 1


@pytest.mark.asyncio
async def test_delete_task(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """DELETE /api/tasks/:id removes task."""
    board = await _create_board(auth_client, answered_goal.id)
    task_id = board["columns"][0]["tasks"][0]["id"]
    original_count = len(board["columns"][0]["tasks"])

    response = await auth_client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    col = next(c for c in data["columns"] if c["id"] == board["columns"][0]["id"])
    assert len(col["tasks"]) == original_count - 1


@pytest.mark.asyncio
async def test_task_not_found(
    auth_client: AsyncClient,
) -> None:
    """Operations on nonexistent task return 404."""
    response = await auth_client.patch(
        "/api/tasks/nonexistent",
        json={"title": "Test"},
    )
    assert response.status_code == 404

    response = await auth_client.delete("/api/tasks/nonexistent")
    assert response.status_code == 404
