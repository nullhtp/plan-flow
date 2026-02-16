"""Integration tests for subtask CRUD endpoints."""

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
async def test_create_subtask(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """POST /api/tasks/:id/subtasks creates a new subtask."""
    board = await _create_board(auth_client, answered_goal.id)
    task_id = board["columns"][0]["tasks"][0]["id"]

    response = await auth_client.post(
        f"/api/tasks/{task_id}/subtasks",
        json={"title": "Sub-item 1"},
    )
    assert response.status_code == 201
    data = response.json()
    task = next(t for c in data["columns"] for t in c["tasks"] if t["id"] == task_id)
    assert len(task["subtasks"]) == 1
    assert task["subtasks"][0]["title"] == "Sub-item 1"
    assert task["subtasks"][0]["completed"] is False


@pytest.mark.asyncio
async def test_toggle_subtask(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """PATCH /api/subtasks/:id toggles completed status."""
    board = await _create_board(auth_client, answered_goal.id)
    task_id = board["columns"][0]["tasks"][0]["id"]

    # Create subtask
    create_response = await auth_client.post(
        f"/api/tasks/{task_id}/subtasks",
        json={"title": "Toggle me"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    task = next(t for c in data["columns"] for t in c["tasks"] if t["id"] == task_id)
    subtask_id = task["subtasks"][0]["id"]

    # Toggle to completed
    response = await auth_client.patch(
        f"/api/subtasks/{subtask_id}",
        json={"completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    task = next(t for c in data["columns"] for t in c["tasks"] if t["id"] == task_id)
    assert task["subtasks"][0]["completed"] is True


@pytest.mark.asyncio
async def test_delete_subtask(
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """DELETE /api/subtasks/:id removes the subtask."""
    board = await _create_board(auth_client, answered_goal.id)
    task_id = board["columns"][0]["tasks"][0]["id"]

    # Create subtask
    create_response = await auth_client.post(
        f"/api/tasks/{task_id}/subtasks",
        json={"title": "Delete me"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    task = next(t for c in data["columns"] for t in c["tasks"] if t["id"] == task_id)
    subtask_id = task["subtasks"][0]["id"]

    # Delete
    response = await auth_client.delete(f"/api/subtasks/{subtask_id}")
    assert response.status_code == 200
    data = response.json()
    task = next(t for c in data["columns"] for t in c["tasks"] if t["id"] == task_id)
    assert len(task["subtasks"]) == 0


@pytest.mark.asyncio
async def test_subtask_not_found(
    auth_client: AsyncClient,
) -> None:
    """Operations on nonexistent subtask return 404."""
    response = await auth_client.patch(
        "/api/subtasks/nonexistent",
        json={"completed": True},
    )
    assert response.status_code == 404

    response = await auth_client.delete("/api/subtasks/nonexistent")
    assert response.status_code == 404
