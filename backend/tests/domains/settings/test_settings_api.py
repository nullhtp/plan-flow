"""Integration tests for user settings API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings_creates_defaults(auth_client: AsyncClient) -> None:
    """GET /api/settings returns default settings (lazy creation)."""
    response = await auth_client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["memory_enabled"] is True


@pytest.mark.asyncio
async def test_patch_settings_toggle_memory(auth_client: AsyncClient) -> None:
    """PATCH /api/settings toggles memory_enabled."""
    # Disable memory
    response = await auth_client.patch(
        "/api/settings",
        json={"memory_enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["memory_enabled"] is False

    # Verify persisted
    response = await auth_client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["memory_enabled"] is False

    # Re-enable
    response = await auth_client.patch(
        "/api/settings",
        json={"memory_enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["memory_enabled"] is True


@pytest.mark.asyncio
async def test_get_settings_simple_mode_defaults_true(auth_client: AsyncClient) -> None:
    """GET /api/settings returns simple_mode enabled by default."""
    response = await auth_client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["simple_mode"] is True


@pytest.mark.asyncio
async def test_patch_settings_toggle_simple_mode(auth_client: AsyncClient) -> None:
    """PATCH /api/settings toggles simple_mode independently of memory_enabled."""
    # Disable simple mode
    response = await auth_client.patch(
        "/api/settings",
        json={"simple_mode": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["simple_mode"] is False
    # Unrelated setting is untouched
    assert body["memory_enabled"] is True

    # Verify persisted
    response = await auth_client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["simple_mode"] is False

    # Re-enable
    response = await auth_client.patch(
        "/api/settings",
        json={"simple_mode": True},
    )
    assert response.status_code == 200
    assert response.json()["simple_mode"] is True


@pytest.mark.asyncio
async def test_settings_requires_auth(client: AsyncClient) -> None:
    """Settings endpoints require authentication."""
    response = await client.get("/api/settings")
    assert response.status_code == 401
