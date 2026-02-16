from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QuestionSchema(BaseModel):
    """A single AI-generated question for the dynamic form."""

    id: str
    text: str
    type: str = Field(description="One of: text, select, multiselect, number")
    options: list[str] | None = None
    rationale: str
    required: bool = True


class GoalCreate(BaseModel):
    """Request body for creating a new goal."""

    original_input: str = Field(min_length=1, max_length=2000)


class GoalQuestionsResponse(BaseModel):
    """Successful goal creation response with generated questions."""

    goal_id: str
    title: str
    status: str
    questions: list[QuestionSchema]


class GoalRejectionResponse(BaseModel):
    """Response when a goal is rejected as too vague."""

    rejection_reason: str
    refinement_suggestions: list[str]


class AnswerSubmission(BaseModel):
    """Request body for submitting answers to generated questions."""

    answers: dict[str, Any]
    round: int = Field(ge=1, le=2)


class AnswerResponse(BaseModel):
    """Response after submitting answers."""

    is_complete: bool
    follow_up_questions: list[QuestionSchema] = Field(  # pyright: ignore[reportUnknownVariableType]
        default_factory=list,
    )
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
