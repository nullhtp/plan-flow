from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClassificationOutput(BaseModel):
    """Structured output from the goal classification LLM call."""

    domain: str = Field(
        description="Goal domain category, e.g. 'relocation'",
    )
    complexity: int = Field(
        description="Estimated complexity from 1 (simple) to 5 (very complex)",
    )
    confidence: float = Field(
        description="Confidence that the goal is actionable (0-1)",
    )
    dimensions: list[str] = Field(
        description="Key aspects/dimensions to explore via questions"
    )
    suggested_title: str = Field(
        description="A clean, concise title derived from the raw input"
    )
    language: str = Field(
        default="en",
        description="ISO 639-1 language code detected from the input, e.g. 'en', 'ru', 'es'",  # noqa: E501
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
        description="3-7 adaptive questions for the user",
    )


class FollowUpInput(BaseModel):
    """Input context for generating follow-up questions."""

    classification: ClassificationOutput
    questions: list[QuestionItem]
    answers: dict[str, Any]


class BoardGenerationTaskOutput(BaseModel):
    """A single task in the AI-generated board output (DAG node)."""

    id: str = Field(
        description="Unique task identifier within the board, e.g. 't1', 't2'",
    )
    title: str = Field(description="Concise, actionable task title")
    description: str = Field(
        description="Brief description of what this task involves",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="List of task IDs this task depends on (prerequisites). "
        "Empty means the task can be started immediately.",
    )
    is_goal_node: bool = Field(
        default=False,
        description="True for the single final goal completion task. "
        "Exactly one task must have this set to true.",
    )
    due_date: str | None = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) if relevant",
    )
    priority: str | None = Field(
        default=None,
        description="'low', 'medium', or 'high' if relevant",
    )
    estimated_minutes: int | None = Field(
        default=None,
        description="Estimated time in minutes if relevant",
    )


class BoardGenerationOutput(BaseModel):
    """Structured output from the board generation LLM call (DAG-based).

    NOTE: Legacy schema kept temporarily for backward compatibility during migration.
    New code should use BoardSkeletonOutput + TaskEnrichmentOutput.
    """

    board_title: str = Field(description="A concise title for the board")
    tasks: list[BoardGenerationTaskOutput] = Field(
        description="Flat list of tasks forming a DAG (5-30 tasks)",
    )


# ── Chat Response Schemas (AI tool use) ──────────────────


class ToolAction(BaseModel):
    """A single tool action executed (or proposed) during a chat turn."""

    tool_name: str = Field(description="Name of the tool that was called")
    description: str = Field(description="Human-readable description of the action")
    status: str = Field(
        description="Outcome: 'executed', 'pending_confirmation', or 'failed'"
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="Tool-specific result data (null for pending/failed)",
    )


class ChatResponse(BaseModel):
    """Unified response from task or board chat endpoints.

    Backward-compatible with the original TaskChatResponse: the new fields
    default to empty/None so old clients continue to work.
    """

    response: str = Field(description="The AI assistant's natural-language response")
    thread_id: str = Field(description="The conversation thread ID")
    actions: list[ToolAction] = Field(
        default_factory=list,
        description="Tools used during this chat turn",
    )
    pending_action_id: str | None = Field(
        default=None,
        description="If a destructive action awaits confirmation, its ID",
    )


# ── Chat Request / Response Schemas (moved from ai/router.py) ──


class TaskChatRequest(BaseModel):
    """Request body for the task chat endpoint."""

    message: str = Field(
        min_length=1,
        max_length=4000,
        description="The user's chat message",
    )


class BoardChatRequest(BaseModel):
    """Request body for the board chat endpoint."""

    message: str = Field(
        min_length=1,
        max_length=4000,
        description="The user's chat message",
    )


class TaskChatResponse(BaseModel):
    """Response from the task chat endpoint (legacy, kept for backward compat)."""

    response: str = Field(description="The AI assistant's response")
    thread_id: str = Field(description="The conversation thread ID")


class ActionConfirmResponse(BaseModel):
    """Response from confirm/reject action endpoints."""

    status: str = Field(
        description="Outcome: executed, rejected, failed, expired, etc."
    )
    description: str | None = Field(default=None)
    error: str | None = Field(default=None)
    result: dict | None = Field(default=None)  # pyright: ignore[reportMissingTypeArgument]
