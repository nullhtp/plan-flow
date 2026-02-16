"""Integration tests for ownership validation (cross-user access returns 404)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.ai.schemas import (
    BoardGenerationColumnOutput,
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)
from app.domains.auth.models import User
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
@patch("app.domains.boards.service.generate_board_from_context")
async def test_other_user_cannot_access_board(
    mock_ai,
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """A different user cannot view or modify another user's board."""
    mock_ai.return_value = _mock_board_output()

    # Create board as the test user
    response = await auth_client.post(f"/api/goals/{answered_goal.id}/generate-board")
    assert response.status_code == 201
    board_id = response.json()["id"]
    column_id = response.json()["columns"][0]["id"]
    task_id = response.json()["columns"][0]["tasks"][0]["id"]

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
    assert (await auth_client.get(f"/api/boards/{board_id}")).status_code == 404
    assert (
        await auth_client.patch(f"/api/boards/{board_id}", json={"title": "Hacked"})
    ).status_code == 404
    assert (
        await auth_client.post(
            f"/api/boards/{board_id}/columns", json={"title": "Evil"}
        )
    ).status_code == 404
    assert (
        await auth_client.patch(f"/api/columns/{column_id}", json={"title": "Evil"})
    ).status_code == 404
    assert (await auth_client.delete(f"/api/columns/{column_id}")).status_code == 404
    assert (
        await auth_client.post(
            f"/api/columns/{column_id}/tasks", json={"title": "Evil"}
        )
    ).status_code == 404
    assert (
        await auth_client.patch(f"/api/tasks/{task_id}", json={"title": "Evil"})
    ).status_code == 404
    assert (await auth_client.delete(f"/api/tasks/{task_id}")).status_code == 404
