from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClassificationOutput(BaseModel):
    """Structured output from the goal classification LLM call."""

    domain: str = Field(
        description="Goal domain category, e.g. 'relocation'",
    )
    complexity: int = Field(
        ge=1,
        le=5,
        description="Estimated complexity from 1 (simple) to 5 (very complex)",
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence that the goal is actionable (0-1)"
    )
    dimensions: list[str] = Field(
        description="Key aspects/dimensions to explore via questions"
    )
    suggested_title: str = Field(
        description="A clean, concise title derived from the raw input"
    )
    rejection_reason: str | None = Field(
        default=None,
        description="If confidence is low, explain why the goal is too vague",
    )
    refinement_suggestions: list[str] = Field(
        default_factory=list,
        description="2-3 alternative goal descriptions if too vague",
    )


class QuestionItem(BaseModel):
    """A single question in the AI-generated question set."""

    id: str = Field(description="Unique question ID, e.g. 'q1', 'q2'")
    text: str = Field(description="The question text")
    type: str = Field(description="Field type: text, select, multiselect, or number")
    options: list[str] | None = Field(
        default=None,
        description="Options for select/multiselect fields, null for text/number",
    )
    rationale: str = Field(description="Why this question matters for planning")
    required: bool = Field(
        default=True, description="Whether the question must be answered"
    )


class QuestionsOutput(BaseModel):
    """Structured output from the question generation LLM call."""

    questions: list[QuestionItem] = Field(
        min_length=3,
        max_length=7,
        description="3-7 adaptive questions for the user",
    )


class FollowUpInput(BaseModel):
    """Input context for generating follow-up questions."""

    classification: ClassificationOutput
    questions: list[QuestionItem]
    answers: dict[str, Any]
