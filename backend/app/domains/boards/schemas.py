from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

# ── Response Schemas ─────────────────────────────────────


class SubtaskResponse(BaseModel):
    """Response schema for a subtask within a task."""

    id: str
    title: str
    completed: bool
    position: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """Response schema for a task within a column."""

    id: str
    title: str
    description: str
    position: str
    due_date: date | None = None
    priority: str | None = None
    estimated_minutes: int | None = None
    subtasks: list[SubtaskResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ColumnResponse(BaseModel):
    """Response schema for a column with nested tasks."""

    id: str
    title: str
    description: str
    position: str
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


class BoardListResponse(BaseModel):
    """Board list item with summary stats."""

    id: str
    goal_id: str
    title: str
    goal_title: str
    column_count: int
    task_count: int
    completed_task_count: int
    created_at: datetime


# ── Create/Update Schemas ────────────────────────────────


class BoardUpdate(BaseModel):
    """Schema for updating a board."""

    title: str


class ColumnCreate(BaseModel):
    """Schema for creating a new column."""

    title: str
    description: str = ""


class ColumnUpdate(BaseModel):
    """Schema for updating a column."""

    title: str | None = None
    description: str | None = None
    position: str | None = None


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    title: str
    description: str = ""
    due_date: date | None = None
    priority: str | None = None
    estimated_minutes: int | None = None


class TaskUpdate(BaseModel):
    """Update a task. Includes optional column_id for moves."""

    title: str | None = None
    description: str | None = None
    position: str | None = None
    column_id: str | None = None
    due_date: date | None = None
    priority: str | None = None
    estimated_minutes: int | None = None


class SubtaskCreate(BaseModel):
    """Schema for creating a new subtask."""

    title: str


class SubtaskUpdate(BaseModel):
    """Schema for updating a subtask."""

    title: str | None = None
    completed: bool | None = None
    position: str | None = None
