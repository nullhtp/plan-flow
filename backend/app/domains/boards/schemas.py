from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class TaskResponse(BaseModel):
    """Response schema for a task within a column."""

    id: str
    title: str
    description: str
    position: int
    due_date: date | None = None
    priority: str | None = None
    estimated_minutes: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ColumnResponse(BaseModel):
    """Response schema for a column with nested tasks."""

    id: str
    title: str
    description: str
    position: int
    tasks: list[TaskResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class BoardResponse(BaseModel):
    """Response schema for a full board with nested columns and tasks."""

    id: str
    goal_id: str
    title: str
    columns: list[ColumnResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class BoardSummaryResponse(BaseModel):
    """Lightweight board response without nested data."""

    id: str
    goal_id: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}
