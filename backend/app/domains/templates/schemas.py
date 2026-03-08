"""Request/response schemas for the templates domain."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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


class UpdateTemplateStructureSubtaskInput(BaseModel):
    """A subtask in the update-structure request."""

    title: str = Field(min_length=1, max_length=500)


class UpdateTemplateStructureTaskInput(BaseModel):
    """A task in the update-structure request."""

    id: str | None = Field(
        default=None, description="Temporary ID used for dependency resolution"
    )
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    is_goal_node: bool = False
    depends_on: list[str] = Field(default_factory=list)
    subtasks: list[UpdateTemplateStructureSubtaskInput] = Field(default_factory=list)
    priority: str | None = Field(
        default=None, description="Task priority: low, medium, or high"
    )
    estimated_minutes: int | None = Field(
        default=None, description="Estimated time in minutes"
    )


class UpdateTemplateStructureRequest(BaseModel):
    """Request body for replacing a template's task structure."""

    tasks: list[UpdateTemplateStructureTaskInput] = Field(min_length=1)


# ── Template Generation Schemas ────────────────────────


class ContentExtractionResponse(BaseModel):
    """Response from content extraction endpoint."""

    content: str
    source_type: str
    source_name: str
    char_count: int
    truncated: bool = False


class ExtractUrlRequest(BaseModel):
    """Request body for URL content extraction."""

    url: str = Field(min_length=1, max_length=2000)


class GenerateTemplateRequest(BaseModel):
    """Request body for AI template generation."""

    content: str = Field(min_length=20, max_length=50000)
    title: str | None = Field(default=None, max_length=200)
    source_description: str | None = Field(default=None, max_length=500)


class GenerateTemplateSubtaskResponse(BaseModel):
    """A subtask in the generation response."""

    title: str


class GenerateTemplateTaskResponse(BaseModel):
    """A task in the generation response."""

    id: str
    title: str
    description: str
    is_goal_node: bool
    depends_on: list[str]
    subtasks: list[GenerateTemplateSubtaskResponse] = []


class GenerateTemplateResponse(BaseModel):
    """Response from template generation endpoint (draft for preview)."""

    suggested_title: str
    suggested_description: str
    suggested_category_slug: str
    tasks: list[GenerateTemplateTaskResponse] = []
    task_count: int


class GenerateTemplateSubtaskInput(BaseModel):
    """A subtask in the save-generated request."""

    title: str = Field(min_length=1, max_length=500)


class GenerateTemplateTaskInput(BaseModel):
    """A task in the save-generated request."""

    id: str | None = Field(
        default=None, description="Temporary ID used for dependency resolution"
    )
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    is_goal_node: bool = False
    depends_on: list[str] = Field(default_factory=list)
    subtasks: list[GenerateTemplateSubtaskInput] = Field(default_factory=list)
    priority: str | None = Field(
        default=None, description="Task priority: low, medium, or high"
    )
    estimated_minutes: int | None = Field(
        default=None, description="Estimated time in minutes"
    )


class SaveGeneratedTemplateRequest(BaseModel):
    """Request body for saving a generated (and optionally edited) template."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    category_id: str | None = None
    visibility: str = "private"
    tasks: list[GenerateTemplateTaskInput] = Field(min_length=1)
    create_board: bool = Field(
        default=False,
        description="If true, also create a board from the saved template",
    )


# ── Template Classification & Question Schemas ─────────


class TemplateQuestionSchema(BaseModel):
    """A single AI-generated question for the template question form."""

    id: str
    text: str
    type: str = Field(description="One of: text, select, multiselect, number")
    options: list[str] = Field(
        min_length=3,
        max_length=6,
        description=("3-6 selectable options. Required for all question types."),
    )
    rationale: str
    required: bool = True
    allow_other: bool = True


class TemplateReadinessSchema(BaseModel):
    """Readiness assessment for template generation."""

    score: float = Field(description="0.0-1.0 readiness score")
    covered_dimensions: list[str] = Field(default_factory=list)
    uncovered_dimensions: list[str] = Field(default_factory=list)
    summary: str = Field(default="")


class TemplateClassifyRequest(BaseModel):
    """Request body for template classification."""

    input_type: str = Field(
        description="Input type: 'describe', 'text', 'file', or 'url'",
    )
    content: str = Field(
        min_length=1,
        max_length=50000,
        description="The input content — description text or pre-extracted content",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional title hint for the template",
    )


class TemplateClassificationData(BaseModel):
    """Classification data returned from the classify endpoint."""

    domain: str
    complexity: int
    confidence: float
    dimensions: list[str]
    suggested_title: str
    language: str


class TemplateClassifyResponse(BaseModel):
    """Response from the template classify endpoint."""

    classification: TemplateClassificationData
    questions: list[TemplateQuestionSchema]
    readiness: TemplateReadinessSchema | None = None
    is_rejected: bool = False
    rejection_reason: str | None = None
    refinement_suggestions: list[str] = Field(default_factory=list)


class TemplateAnswerSubmission(BaseModel):
    """Request body for submitting answers to template questions."""

    answers: dict[str, Any]
    round: int = Field(ge=1, le=2, description="Round number (max 2)")
    classification: TemplateClassificationData
    previous_rounds: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Previous Q&A rounds for context",
    )
    content: str | None = Field(
        default=None,
        max_length=50000,
        description="Original source content (for content-based inputs)",
    )
    raw_input: str = Field(
        min_length=1,
        max_length=50000,
        description="Original input text (description or content summary)",
    )


class TemplateAnswerResponse(BaseModel):
    """Response after submitting template answers."""

    next_questions: list[TemplateQuestionSchema] = Field(default_factory=list)
    readiness: TemplateReadinessSchema | None = None
    next_round: int
    is_ready: bool = Field(
        default=False,
        description="True when no more question rounds are needed",
    )


class TemplateGenerateStreamRequest(BaseModel):
    """Request body for streaming template generation."""

    raw_input: str = Field(
        min_length=1,
        max_length=50000,
        description="Original input text (description or content)",
    )
    classification: TemplateClassificationData
    qa_rounds: list[dict[str, Any]] = Field(
        default_factory=list,
        description="All Q&A rounds (questions + answers)",
    )
    content: str | None = Field(
        default=None,
        max_length=50000,
        description="Source content (for content-based inputs)",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional title for the template",
    )
