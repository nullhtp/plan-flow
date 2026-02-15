from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    """Successful registration returns 201 with user data and sets cookies."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data

    # Verify cookies are set
    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    """Registering with an existing email returns 409."""
    await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )
    response = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "password456"},
    )
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email_case_insensitive(
    client: AsyncClient,
) -> None:
    """Email uniqueness is case-insensitive."""
    await client.post(
        "/api/auth/register",
        json={"email": "User@Example.com", "password": "password123"},
    )
    response = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "password456"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient) -> None:
    """Invalid email format returns 422."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient) -> None:
    """Password shorter than 8 characters returns 422."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 422
