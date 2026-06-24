"""Request/response schemas for user settings."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserSettingsResponse(BaseModel):
    """Response schema for user settings."""

    memory_enabled: bool = Field(
        description="Whether AI memory is enabled for this user"
    )
    simple_mode: bool = Field(
        description="Whether the simplified interface is enabled for this user"
    )


class UserSettingsUpdateRequest(BaseModel):
    """Request schema for updating user settings."""

    memory_enabled: bool | None = Field(
        default=None,
        description="Toggle AI memory on/off for this user",
    )
    simple_mode: bool | None = Field(
        default=None,
        description="Toggle the simplified interface on/off for this user",
    )
