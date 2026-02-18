from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

# ── Response Schemas ─────────────────────────────────────


class SubtaskResponse(BaseModel):
    """Response schema for a subtask within a task."""

    id: str
    title: str
    completed: bool
    position: str
    action_label: str | None = None
    action_icon: str | None = None
    action_prompt: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EdgeResponse(BaseModel):
    """A single dependency edge in the DAG."""

    source: str  # dependency_task_id (prerequisite)
    target: str  # dependent_task_id (blocked task)


class TaskResponse(BaseModel):
    """Response schema for a task within a board."""

    id: str
    title: str
    description: str
    status: str
    is_goal_node: bool
    due_date: date | None = None
    priority: str | None = None
    estimated_minutes: int | None = None
    subtasks: list[SubtaskResponse] = []
    dependency_ids: list[str] = []
    dependent_ids: list[str] = []
    is_locked: bool = False
    artifact_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class BoardResponse(BaseModel):
    """Response schema for a full board with nested tasks and dependency edges."""

    id: str
    goal_id: str
    title: str
    tasks: list[TaskResponse]
    edges: list[EdgeResponse]
    is_completed: bool = False
    user_meta: dict[str, Any] | None = None
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
    task_count: int
    completed_task_count: int
    created_at: datetime


# ── Create/Update Schemas ────────────────────────────────


class BoardUpdate(BaseModel):
    """Schema for updating a board."""

    title: str


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    title: str
    description: str = ""
    due_date: date | None = None
    priority: str | None = None
    estimated_minutes: int | None = None


class TaskUpdate(BaseModel):
    """Update a task. Includes optional status for transitions."""

    title: str | None = None
    description: str | None = None
    status: str | None = None
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


# ── Artifact Schemas ─────────────────────────────────────


class ArtifactResponse(BaseModel):
    """Response schema for a task artifact."""

    id: str
    task_id: str
    title: str
    content: str
    content_type: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactListResponse(BaseModel):
    """Response containing a list of artifacts."""

    artifacts: list[ArtifactResponse]
