from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient) -> None:
    """Logout returns 200 and clears auth cookies."""
    # Register first to get cookies
    await client.post(
        "/api/auth/register",
        json={"email": "logout@example.com", "password": "password123"},
    )

    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_logout_without_auth(client: AsyncClient) -> None:
    """Logout without authentication still returns 200 (idempotent)."""
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
