"""Integration tests for task CRUD endpoints (DAG-based)."""

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
    """Find a task by title in a board response."""
    return next(t for t in data["tasks"] if t["title"] == title)


@pytest.mark.asyncio
async def test_create_task(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """POST /api/boards/:id/tasks creates a new task on the board."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    original_count = len(board_data["tasks"])

    response = await auth_client.post(
        f"/api/boards/{board_data['id']}/tasks",
        json={
            "title": "New Task",
            "description": "A new task",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["tasks"]) == original_count + 1
    new_task = _find_task(data, "New Task")
    assert new_task["priority"] == "high"
    assert new_task["status"] == "not_started"
    assert new_task["is_goal_node"] is False


@pytest.mark.asyncio
async def test_update_task_title(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """PATCH /api/tasks/:id updates task title."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    task = _find_task(board_data, "Task 1")

    response = await auth_client.patch(
        f"/api/tasks/{task['id']}",
        json={"title": "Updated Title"},
    )
    assert response.status_code == 200
    data = response.json()
    updated = next(t for t in data["tasks"] if t["id"] == task["id"])
    assert updated["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_task_status_to_in_progress(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """PATCH /api/tasks/:id can transition root task to in_progress."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    # Task 1 has no deps, so it can start
    task = _find_task(board_data, "Task 1")

    response = await auth_client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    data = response.json()
    updated = next(t for t in data["tasks"] if t["id"] == task["id"])
    assert updated["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_task_status_blocked_by_deps(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """Cannot start a task when its dependencies are not done."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    goal_task = _find_task(board_data, "Goal Task")

    response = await auth_client.patch(
        f"/api/tasks/{goal_task['id']}",
        json={"status": "in_progress"},
    )
    assert response.status_code == 409
    assert "dependencies" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_task_status_skip_to_done_rejected(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """Cannot go directly from not_started to done."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    task = _find_task(board_data, "Task 1")

    response = await auth_client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "done"},
    )
    assert response.status_code == 409
    assert "in progress" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_task_status_full_flow(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """Full status flow: not_started -> in_progress -> done."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    task = _find_task(board_data, "Task 1")

    # Start
    response = await auth_client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200

    # Complete
    response = await auth_client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "done"},
    )
    assert response.status_code == 200
    data = response.json()
    updated = next(t for t in data["tasks"] if t["id"] == task["id"])
    assert updated["status"] == "done"


@pytest.mark.asyncio
async def test_completing_deps_unlocks_dependent(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """Completing all dependencies makes dependent task unlocked."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    task1 = _find_task(board_data, "Task 1")
    task2 = _find_task(board_data, "Task 2")
    goal_task = _find_task(board_data, "Goal Task")

    # Goal task should be locked initially
    assert goal_task["is_locked"] is True

    # Complete task 1
    await auth_client.patch(f"/api/tasks/{task1['id']}", json={"status": "in_progress"})
    await auth_client.patch(f"/api/tasks/{task1['id']}", json={"status": "done"})

    # Goal task still locked (task 2 not done)
    response = await auth_client.get(f"/api/boards/{board_data['id']}")
    data = response.json()
    assert _find_task(data, "Goal Task")["is_locked"] is True

    # Complete task 2
    await auth_client.patch(f"/api/tasks/{task2['id']}", json={"status": "in_progress"})
    await auth_client.patch(f"/api/tasks/{task2['id']}", json={"status": "done"})

    # Goal task should now be unlocked
    response = await auth_client.get(f"/api/boards/{board_data['id']}")
    data = response.json()
    assert _find_task(data, "Goal Task")["is_locked"] is False


@pytest.mark.asyncio
async def test_completing_goal_marks_board_completed(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """Setting goal node to done makes is_completed true."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    task1 = _find_task(board_data, "Task 1")
    task2 = _find_task(board_data, "Task 2")
    goal_task = _find_task(board_data, "Goal Task")

    # Complete prerequisites
    await auth_client.patch(f"/api/tasks/{task1['id']}", json={"status": "in_progress"})
    await auth_client.patch(f"/api/tasks/{task1['id']}", json={"status": "done"})
    await auth_client.patch(f"/api/tasks/{task2['id']}", json={"status": "in_progress"})
    await auth_client.patch(f"/api/tasks/{task2['id']}", json={"status": "done"})

    # Start and complete goal
    await auth_client.patch(
        f"/api/tasks/{goal_task['id']}", json={"status": "in_progress"}
    )
    response = await auth_client.patch(
        f"/api/tasks/{goal_task['id']}", json={"status": "done"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_completed"] is True


@pytest.mark.asyncio
async def test_delete_task(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """DELETE /api/tasks/:id removes task and its dependency edges."""
    board_data = await _create_board_and_get(auth_client, session, answered_goal)
    task = _find_task(board_data, "Task 1")
    original_count = len(board_data["tasks"])

    response = await auth_client.delete(f"/api/tasks/{task['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == original_count - 1
    # Verify the deleted task's edges are gone
    for edge in data["edges"]:
        assert edge["source"] != task["id"]
        assert edge["target"] != task["id"]


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
