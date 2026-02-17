"""Integration tests for subtask CRUD endpoints (DAG-based)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.goals.models import Goal
from tests.conftest import create_test_board


async def _create_board_and_get(
    auth_client: AsyncClient, session: AsyncSession, goal: Goal
) -> dict:
    """Create a board via helper and return its JSON representation."""
    board, _ = await create_test_board(session, goal)
    response = await auth_client.get(f"/api/boards/{board.id}")
    assert response.status_code == 200
    return response.json()


def _find_task(data: dict, title: str) -> dict:
    return next(t for t in data["tasks"] if t["title"] == title)


@pytest.mark.asyncio
async def test_create_subtask(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """POST /api/tasks/:id/subtasks creates a new subtask."""
    board = await _create_board_and_get(auth_client, session, answered_goal)
    task = _find_task(board, "Task 1")

    response = await auth_client.post(
        f"/api/tasks/{task['id']}/subtasks",
        json={"title": "Sub-item 1"},
    )
    assert response.status_code == 201
    data = response.json()
    updated_task = next(t for t in data["tasks"] if t["id"] == task["id"])
    assert len(updated_task["subtasks"]) == 1
    assert updated_task["subtasks"][0]["title"] == "Sub-item 1"
    assert updated_task["subtasks"][0]["completed"] is False


@pytest.mark.asyncio
async def test_toggle_subtask(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """PATCH /api/subtasks/:id toggles completed status."""
    board = await _create_board_and_get(auth_client, session, answered_goal)
    task = _find_task(board, "Task 1")

    # Create subtask
    create_response = await auth_client.post(
        f"/api/tasks/{task['id']}/subtasks",
        json={"title": "Toggle me"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    updated_task = next(t for t in data["tasks"] if t["id"] == task["id"])
    subtask_id = updated_task["subtasks"][0]["id"]

    # Toggle to completed
    response = await auth_client.patch(
        f"/api/subtasks/{subtask_id}",
        json={"completed": True},
    )
    assert response.status_code == 200
    data = response.json()
    updated_task = next(t for t in data["tasks"] if t["id"] == task["id"])
    assert updated_task["subtasks"][0]["completed"] is True


@pytest.mark.asyncio
async def test_delete_subtask(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """DELETE /api/subtasks/:id removes the subtask."""
    board = await _create_board_and_get(auth_client, session, answered_goal)
    task = _find_task(board, "Task 1")

    # Create subtask
    create_response = await auth_client.post(
        f"/api/tasks/{task['id']}/subtasks",
        json={"title": "Delete me"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    updated_task = next(t for t in data["tasks"] if t["id"] == task["id"])
    subtask_id = updated_task["subtasks"][0]["id"]

    # Delete
    response = await auth_client.delete(f"/api/subtasks/{subtask_id}")
    assert response.status_code == 200
    data = response.json()
    updated_task = next(t for t in data["tasks"] if t["id"] == task["id"])
    assert len(updated_task["subtasks"]) == 0


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
