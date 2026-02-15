from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.domains.auth.models import User


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient, test_user: User) -> None:
    """Valid refresh token returns 200 with new cookies."""
    # Login to get cookies
    await client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )

    # The refresh token cookie is scoped to /api/auth/refresh,
    # so we need to explicitly pass it
    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token is not None

    response = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_refresh_expired_token(client: AsyncClient) -> None:
    """Expired refresh token returns 401."""
    expire = datetime.now(UTC) - timedelta(hours=1)
    payload = {"sub": "user-expired", "exp": expire, "type": "refresh"}
    expired_token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    response = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": expired_token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_missing_token(client: AsyncClient) -> None:
    """Missing refresh token returns 401."""
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401
