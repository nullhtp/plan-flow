from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.domains.auth.models import User


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, test_user: User) -> None:
    """Authenticated user can retrieve their profile."""
    # Login to get cookies
    await client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )

    access_token = client.cookies.get("access_token")
    assert access_token is not None

    response = await client.get(
        "/api/auth/me",
        cookies={"access_token": access_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["id"] == test_user.id
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient) -> None:
    """Unauthenticated request returns 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
