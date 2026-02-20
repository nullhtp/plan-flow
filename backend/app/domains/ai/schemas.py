from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ── Memory Management Schemas ────────────────────────────


class MemoryResponse(BaseModel):
    """Response schema for a single memory."""

    id: str = Field(description="Memory ID")
    content: str = Field(description="Memory content text")
    category: str = Field(
        description="Memory category: preference, fact, pattern, context"
    )
    source_stage: str = Field(description="Pipeline stage that created this memory")
    created_at: str = Field(description="ISO timestamp of creation")
    last_used_at: str | None = Field(
        default=None, description="ISO timestamp of last retrieval"
    )


class MemoryListResponse(BaseModel):
    """Paginated list of memories."""

    items: list[MemoryResponse] = Field(description="List of memories")
    total: int = Field(description="Total count of memories matching the filter")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")


class MemoryUpdateRequest(BaseModel):
    """Request schema for updating a memory."""

    content: str = Field(
        min_length=1,
        max_length=2000,
        description="Updated memory content text",
    )


class MemoryBulkDeleteRequest(BaseModel):
    """Request schema for bulk deleting memories."""

    category: str | None = Field(
        default=None,
        description="If set, only delete memories in this category. "
        "If None, delete all user memories.",
    )


class MemoryStatsResponse(BaseModel):
    """Statistics about user's memories."""

    total: int = Field(description="Total active memory count")
    by_category: dict[str, int] = Field(
        description="Count per category (preference, fact, pattern, context)"
    )


# ── Research Schemas ──────────────────────────────────────


class ResearchQueriesOutput(BaseModel):
    """Structured output: LLM-generated search queries for research."""

    reasoning: str = Field(
        default="",
        description="Chain-of-thought explanation of the research strategy",
    )
    queries: list[str] = Field(
        min_length=1,
        max_length=8,
        description="3-8 diverse search queries to gather information for planning",
    )


class SkeletonReviewOutput(BaseModel):
    """Structured output from the skeleton review/revision step."""

    reasoning: str = Field(
        default="",
        description="Chain-of-thought analysis of the skeleton quality",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="List of problems found in the skeleton",
    )
    has_issues: bool = Field(
        default=False,
        description="True if significant issues were found that warrant revision",
    )
    revised_board_title: str | None = Field(
        default=None,
        description="Revised board title, or null if no revision needed",
    )
    revised_tasks: list[dict[str, Any]] | None = Field(
        default=None,
        description="Revised task list (same schema as BoardSkeletonOutput.tasks), "
        "or null if no revision needed. Each dict has id, title, depends_on, is_goal_node.",  # noqa: E501
    )


# ── AI Pipeline Schemas ─────────────────────────────────


class ClassificationOutput(BaseModel):
    """Structured output from the goal classification LLM call."""

    reasoning: str = Field(
        default="",
        description="Chain-of-thought analysis of the goal",
    )
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
    options: list[str] = Field(
        min_length=3,
        max_length=6,
        description="3-6 selectable options. Required for ALL question types: "
        "suggested answers for text, human-readable ranges for number, "
        "choices for select/multiselect.",
    )
    rationale: str = Field(description="Why this question matters for planning")
    required: bool = Field(
        default=True, description="Whether the question must be answered"
    )
    allow_other: bool = Field(
        default=True,
        description="Whether the UI should render a free-text 'Other' input "
        "alongside the options.",
    )


class ReadinessAssessment(BaseModel):
    """Assessment of how ready the collected information is for board generation."""

    score: float = Field(
        description="Overall readiness score from 0.0 (no info) to 1.0 (fully ready). "
        "0.8+ means enough context for a high-quality board.",
    )
    covered_dimensions: list[str] = Field(
        description="Dimensions from classification that are sufficiently covered "
        "by collected answers.",
    )
    uncovered_dimensions: list[str] = Field(
        description="Dimensions that still lack information.",
    )
    summary: str = Field(
        description="One sentence describing the current readiness state, "
        "in the same language as the goal.",
    )


class QuestionsOutput(BaseModel):
    """Structured output from the question generation LLM call."""

    reasoning: str = Field(
        default="",
        description="Chain-of-thought reasoning about what to ask and why",
    )
    questions: list[QuestionItem] = Field(
        description="2-7 adaptive questions for the user "
        "(3-7 for initial round, 2-4 for follow-up rounds)",
    )
    readiness: ReadinessAssessment = Field(
        description="Assessment of board generation readiness "
        "based on information collected so far.",
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
    used_memory_ids: list[str] = Field(
        default_factory=list,
        description="IDs of memories used to generate this response",
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


# ── Action Suggestion Schemas ────────────────────────────


class ActionSuggestion(BaseModel):
    """A single AI-generated action suggestion for a task."""

    label: str = Field(
        max_length=60,
        description="Short, user-facing button text (e.g., 'Generate agreement draft')",
    )
    icon: str = Field(
        description="Semantic icon hint: generate, research, plan, analyze, "
        "summarize, review, compare, create",
    )
    prompt: str = Field(
        max_length=500,
        description="Natural language message to send to the task chat when clicked",
    )


class ActionSuggestionsResponse(BaseModel):
    """Response from the action suggestion endpoint."""

    actions: list[ActionSuggestion] = Field(
        min_length=2,
        max_length=4,
        description="2-4 contextual action suggestions",
    )


# ── Subtask Action Schemas ────────────────────────────


class SubtaskActionOutput(BaseModel):
    """A single subtask action output from the batch LLM call."""

    subtask_title: str = Field(
        description="Title of the subtask this action applies to (for matching)",
    )
    action_label: str | None = Field(
        default=None,
        max_length=60,
        description="Short button text (e.g., 'Generate agreement draft'), "
        "or null if the subtask cannot be meaningfully automated",
    )
    action_icon: str | None = Field(
        default=None,
        description="Semantic icon hint (generate, research, plan, analyze, "
        "summarize, review, compare, create), or null",
    )
    action_prompt: str | None = Field(
        default=None,
        max_length=500,
        description="Natural language prompt to send to task chat when clicked, "
        "or null",
    )


class SubtaskActionsResponse(BaseModel):
    """Response from the subtask action generation LLM call."""

    actions: list[SubtaskActionOutput] = Field(
        description="One entry per input subtask, with null action fields "
        "for non-automatable subtasks",
    )


class ActionConfirmResponse(BaseModel):
    """Response from confirm/reject action endpoints."""

    status: str = Field(
        description="Outcome: executed, rejected, failed, expired, etc."
    )
    description: str | None = Field(default=None)
    error: str | None = Field(default=None)
    result: dict | None = Field(default=None)  # pyright: ignore[reportMissingTypeArgument]
