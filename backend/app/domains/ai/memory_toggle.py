"""Per-user memory toggle helper.

Checks both the global AI_MEMORY_ENABLED flag and the per-user setting.
Global flag takes priority: if global is off, per-user doesn't matter.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


async def is_memory_enabled(db: AsyncSession, user_id: str) -> bool:
    """Check if memory is enabled for a specific user.

    Rules:
    1. If global AI_MEMORY_ENABLED is False, memory is always disabled.
    2. If global is True, check the per-user setting.
    3. If no per-user setting exists, default to enabled.
    """
    if not settings.ai_memory_enabled:
        return False

    from app.domains.settings.repository import SettingsRepository

    repo = SettingsRepository(db)
    user_settings = await repo.get_by_user_id(user_id)
    if user_settings is None:
        return True  # Default: enabled
    return user_settings.memory_enabled
