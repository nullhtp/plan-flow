"""Integration tests for ownership validation (DAG-based, cross-user access returns 404)."""  # noqa: E501

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.auth.models import User
from app.domains.goals.models import Goal
from tests.conftest import create_test_board


@pytest.mark.asyncio
async def test_other_user_cannot_access_board(
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """A different user cannot view or modify another user's board."""
    board, _ = await create_test_board(session, answered_goal)
    task_id = None

    # Get task IDs from the board
    board_response = await auth_client.get(f"/api/boards/{board.id}")
    assert board_response.status_code == 200
    task_id = board_response.json()["tasks"][0]["id"]

    # Create a second user
    other_user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)

    # Create a client for the other user
    other_token = create_access_token(other_user.id)
    auth_client.cookies.set("access_token", other_token)

    # All endpoints should return 404 for the other user
    assert (await auth_client.get(f"/api/boards/{board.id}")).status_code == 404
    assert (
        await auth_client.patch(f"/api/boards/{board.id}", json={"title": "Hacked"})
    ).status_code == 404
    # Task creation is now board-scoped (not column-scoped)
    assert (
        await auth_client.post(
            f"/api/boards/{board.id}/tasks", json={"title": "Evil", "description": "x"}
        )
    ).status_code == 404
    assert (
        await auth_client.patch(f"/api/tasks/{task_id}", json={"title": "Evil"})
    ).status_code == 404
    assert (await auth_client.delete(f"/api/tasks/{task_id}")).status_code == 404
