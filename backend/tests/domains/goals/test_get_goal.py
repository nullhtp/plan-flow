from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.models import User
from app.domains.goals.models import Goal


@pytest.mark.asyncio
async def test_get_goal_success(
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Get own goal returns full data."""
    response = await auth_client.get(f"/api/goals/{test_goal.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_goal.id
    assert data["title"] == "Relocate to Lisbon"
    assert data["status"] == "questioning"
    assert "ai_context" in data
    assert "questions" in data["ai_context"]


@pytest.mark.asyncio
async def test_get_goal_not_found(auth_client: AsyncClient) -> None:
    """Non-existent goal returns 404."""
    response = await auth_client.get("/api/goals/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_goal_wrong_owner(
    auth_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """Another user's goal returns 404."""
    from app.core.security import hash_password

    other_user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)

    other_goal = Goal(
        user_id=other_user.id,
        title="Other Goal",
        original_input="Some goal",
        status="questioning",
        ai_context={},
    )
    session.add(other_goal)
    await session.commit()
    await session.refresh(other_goal)

    response = await auth_client.get(f"/api/goals/{other_goal.id}")
    assert response.status_code == 404
