from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QuestionSchema(BaseModel):
    """A single AI-generated question for the dynamic form."""

    id: str
    text: str
    type: str = Field(description="One of: text, select, multiselect, number")
    options: list[str] = Field(
        min_length=3,
        max_length=6,
        description=(
            "3-6 selectable options. Required for all question types: "
            "suggested answers for text, ranges for number, "
            "choices for select/multiselect."
        ),
    )
    rationale: str
    required: bool = True
    allow_other: bool = Field(
        default=True,
        description=(
            "Whether the UI should render a free-text "
            "'Other' input alongside the options."
        ),
    )


class ReadinessSchema(BaseModel):
    """Readiness assessment for board generation."""

    score: float = Field(description="0.0-1.0 readiness score")
    covered_dimensions: list[str] = Field(default_factory=list)
    uncovered_dimensions: list[str] = Field(default_factory=list)
    summary: str = Field(default="")


class UserLocationMeta(BaseModel):
    """Location metadata from browser geolocation or IP fallback."""

    city: str | None = None
    country: str | None = None


class UserMeta(BaseModel):
    """User environment context collected at goal creation time."""

    timezone: str  # IANA timezone (e.g., "Europe/Berlin")
    locale: str  # BCP 47 locale (e.g., "en-US", "de-DE")
    current_datetime: str = ""  # ISO 8601 UTC — overridden server-side
    location: UserLocationMeta | None = None
    device_type: str  # "mobile" | "desktop" | "tablet"


class GoalCreate(BaseModel):
    """Request body for creating a new goal."""

    original_input: str = Field(min_length=1, max_length=2000)
    user_meta: UserMeta | None = None


class GoalQuestionsResponse(BaseModel):
    """Successful goal creation response with generated questions."""

    goal_id: str
    title: str
    status: str
    questions: list[QuestionSchema]
    readiness: ReadinessSchema | None = None


class GoalRejectionResponse(BaseModel):
    """Response when a goal is rejected as too vague."""

    rejection_reason: str
    refinement_suggestions: list[str]


class AnswerSubmission(BaseModel):
    """Request body for submitting answers to generated questions."""

    answers: dict[str, Any]
    round: int = Field(ge=1, le=50)


class AnswerResponse(BaseModel):
    """Response after submitting answers.

    Always includes next_questions and readiness.
    The goal stays in 'questioning' status — user decides when to generate.
    """

    next_questions: list[QuestionSchema] = Field(default_factory=list)
    readiness: ReadinessSchema | None = None
    next_round: int
    status: str


class GoalResponse(BaseModel):
    """Full goal data for GET endpoint."""

    id: str
    title: str
    original_input: str
    status: str
    ai_context: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
