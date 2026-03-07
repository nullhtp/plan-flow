"""Request/response schemas for the templates domain."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ── Response Schemas ─────────────────────────────────────


class TemplateCategoryResponse(BaseModel):
    """A template category with public template count."""

    id: str
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    template_count: int = 0


class TemplateCreatorResponse(BaseModel):
    """Lightweight user reference for template attribution."""

    id: str
    email: str


class TemplateCategoryBrief(BaseModel):
    """Category info nested in template responses."""

    id: str
    name: str
    slug: str


class TemplateSubtaskResponse(BaseModel):
    """A subtask within a template task."""

    id: str
    title: str
    position: str

    model_config = {"from_attributes": True}


class TemplateEdgeResponse(BaseModel):
    """A dependency edge in the template's DAG."""

    source: str  # dependency_task_id (prerequisite)
    target: str  # dependent_task_id (blocked task)


class TemplateTaskResponse(BaseModel):
    """A task within a template."""

    id: str
    title: str
    description: str
    is_goal_node: bool
    priority: str | None = None
    estimated_minutes: int | None = None
    subtasks: list[TemplateSubtaskResponse] = []

    model_config = {"from_attributes": True}


class TemplateListItemResponse(BaseModel):
    """Template item in a list response."""

    id: str
    title: str
    description: str | None = None
    visibility: str
    category: TemplateCategoryBrief | None = None
    task_count: int
    creator: TemplateCreatorResponse
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    """Paginated template list response."""

    items: list[TemplateListItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class TemplateDetailResponse(BaseModel):
    """Full template detail with tasks, subtasks, and edges."""

    id: str
    title: str
    description: str | None = None
    visibility: str
    category: TemplateCategoryBrief | None = None
    task_count: int
    creator: TemplateCreatorResponse
    tasks: list[TemplateTaskResponse] = []
    edges: list[TemplateEdgeResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateBoardFromTemplateResponse(BaseModel):
    """Response after creating a board from a template."""

    board_id: str
    goal_id: str
    title: str


# ── Request Schemas ──────────────────────────────────────


class TemplateCreateRequest(BaseModel):
    """Request body for creating a template from a board."""

    board_id: str
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category_id: str | None = None
    visibility: str = "private"


class TemplateUpdateRequest(BaseModel):
    """Request body for updating template metadata."""

    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category_id: str | None = None
    visibility: str | None = None


class CreateBoardFromTemplateRequest(BaseModel):
    """Request body for creating a board from a template."""

    title: str | None = Field(default=None, max_length=200)
