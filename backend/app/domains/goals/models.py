from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field, SQLModel


class GoalStatus(StrEnum):
    """Pipeline-aware status tracking for goals."""

    INPUT = "input"
    CLASSIFYING = "classifying"
    QUESTIONING = "questioning"
    ANSWERED = "answered"
    GENERATING = "generating"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Goal(SQLModel, table=True):
    """A user's goal that the AI pipeline processes into a kanban board."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    user_id: str = Field(foreign_key="user.id", index=True)
    title: str = Field(default="")
    original_input: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(default=GoalStatus.INPUT)
    ai_context: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
