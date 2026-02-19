"""Business logic for user settings."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.settings.models import UserSettings
from app.domains.settings.repository import SettingsRepository


async def get_user_settings(
    session: AsyncSession,
    user_id: str,
) -> UserSettings:
    """Get user settings, creating defaults if needed."""
    repo = SettingsRepository(session)
    return await repo.get_or_create(user_id)


async def update_user_settings(
    session: AsyncSession,
    user_id: str,
    *,
    memory_enabled: bool | None = None,
) -> UserSettings:
    """Update user settings with provided values."""
    repo = SettingsRepository(session)
    user_settings = await repo.get_or_create(user_id)

    if memory_enabled is not None:
        user_settings.memory_enabled = memory_enabled

    return await repo.update(user_settings)
