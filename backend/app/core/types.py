"""Cross-domain Pydantic schemas shared between multiple domains.

These types are consumed by both the AI and boards domains.
Placing them here in core/ eliminates circular dependencies.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BoardSkeletonTaskOutput(BaseModel):
    """A single task in the skeleton output (structure only, no content)."""

    id: str = Field(
        description="Unique task identifier within the board, e.g. 't1', 't2'",
    )
    title: str = Field(description="Concise, actionable task title")
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


class BoardSkeletonOutput(BaseModel):
    """Structured output from the skeleton generation step."""

    board_title: str = Field(description="A concise title for the board")
    tasks: list[BoardSkeletonTaskOutput] = Field(
        description="Flat list of tasks forming a DAG (5-30 tasks). "
        "Only structure — no descriptions or metadata.",
    )


class SubtaskOutput(BaseModel):
    """A single subtask generated during task enrichment."""

    title: str = Field(description="Concise, actionable subtask title")
    action_label: str | None = Field(
        default=None,
        description="Short button text for the AI action (max 60 chars), "
        "or null if the subtask cannot be meaningfully automated",
    )
    action_icon: str | None = Field(
        default=None,
        description="Semantic icon category for the action (generate, research, "
        "plan, analyze, summarize, review, compare, create), or null",
    )
    action_prompt: str | None = Field(
        default=None,
        description="Natural language prompt to send to task chat when the action "
        "is clicked (max 500 chars), or null",
    )


class TaskEnrichmentOutput(BaseModel):
    """Structured output from the per-task enrichment step."""

    description: str = Field(
        description="Clear description of what this task involves",
    )
    due_date: str | None = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) if a specific deadline is relevant",
    )
    priority: str | None = Field(
        default=None,
        description="'low', 'medium', or 'high' if prioritization adds value",
    )
    estimated_minutes: int | None = Field(
        default=None,
        description="Estimated time in minutes if the task has predictable duration",
    )
    subtasks: list[SubtaskOutput] = Field(
        default_factory=list,
        description="2-5 concrete, ordered subtasks that break down the task",
    )


__all__ = [
    "BoardSkeletonOutput",
    "BoardSkeletonTaskOutput",
    "SubtaskOutput",
    "TaskEnrichmentOutput",
]
