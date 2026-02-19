"""Data-access layer for user settings."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.settings.models import UserSettings


class SettingsRepository:
    """Encapsulates all database queries for :class:`UserSettings`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: str) -> UserSettings | None:
        """Fetch settings for a user, or None if not yet created."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: str) -> UserSettings:
        """Get existing settings or create with defaults (lazy creation)."""
        existing = await self.get_by_user_id(user_id)
        if existing is not None:
            return existing

        settings = UserSettings(user_id=user_id)
        self.session.add(settings)
        await self.session.commit()
        await self.session.refresh(settings)
        return settings

    async def update(self, user_settings: UserSettings) -> UserSettings:
        """Persist updated settings."""
        user_settings.updated_at = datetime.now(UTC)
        self.session.add(user_settings)
        await self.session.commit()
        await self.session.refresh(user_settings)
        return user_settings


__all__ = ["SettingsRepository"]
