"""Settings API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domains.auth.deps import CurrentUser
from app.domains.settings.schemas import UserSettingsResponse, UserSettingsUpdateRequest
from app.domains.settings.service import get_user_settings, update_user_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserSettingsResponse:
    """Get current user settings."""
    settings = await get_user_settings(session, current_user.id)
    return UserSettingsResponse(memory_enabled=settings.memory_enabled)


@router.patch("", response_model=UserSettingsResponse)
async def patch_settings(
    body: UserSettingsUpdateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserSettingsResponse:
    """Update user settings."""
    settings = await update_user_settings(
        session,
        current_user.id,
        memory_enabled=body.memory_enabled,
    )
    return UserSettingsResponse(memory_enabled=settings.memory_enabled)
