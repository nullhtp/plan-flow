"""LangGraph pipeline definition for goal understanding.

This module defines the state graph for the classify → generate_questions
flow. Currently the service layer calls nodes directly for simplicity,
but this graph is available for future extension.

Board generation uses a separate two-step streaming flow (skeleton + enrichment)
orchestrated by ai/service.py:generate_board_stream() rather than a LangGraph graph.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph  # pyright: ignore[reportMissingTypeStubs]

from app.core.config import settings
from app.domains.ai.nodes.classify import classify_goal
from app.domains.ai.nodes.questions import generate_questions
from app.domains.ai.schemas import (
    ClassificationOutput,
    QuestionItem,
)


class GoalPipelineState(TypedDict, total=False):
    """State for the goal understanding pipeline."""

    raw_input: str
    classification: ClassificationOutput | None
    questions: list[QuestionItem] | None
    is_rejected: bool
    rejection_reason: str | None
    refinement_suggestions: list[str] | None
    memory_context: str


async def _classify_node(state: GoalPipelineState) -> dict[str, Any]:
    """Classification node: classify the goal and check confidence."""
    raw_input: str = state.get("raw_input", "")  # pyright: ignore[reportTypedDictNotRequiredAccess]
    classification = await classify_goal(raw_input)

    if classification.confidence < settings.ai_confidence_threshold:
        return {
            "classification": classification,
            "is_rejected": True,
            "rejection_reason": classification.rejection_reason
            or "This goal is too vague to create a meaningful plan.",
            "refinement_suggestions": classification.refinement_suggestions,
        }

    return {
        "classification": classification,
        "is_rejected": False,
    }


async def _generate_questions_node(state: GoalPipelineState) -> dict[str, Any]:
    """Question generation node: generate questions from classification."""
    raw_input: str = state.get("raw_input", "")  # pyright: ignore[reportTypedDictNotRequiredAccess]
    classification = state.get("classification")
    if classification is None:
        msg = "Classification must be completed before question generation"
        raise ValueError(msg)

    questions = await generate_questions(raw_input, classification)
    return {"questions": questions}


def _route_after_classify(state: GoalPipelineState) -> str:
    """Route to question generation or end based on rejection status."""
    if state.get("is_rejected", False):
        return END  # pyright: ignore[reportReturnType]
    return "generate_questions"


def build_goal_pipeline() -> StateGraph[GoalPipelineState]:  # pyright: ignore[reportMissingTypeArgument]
    """Build the LangGraph state graph for goal understanding."""
    graph: StateGraph[GoalPipelineState] = StateGraph(GoalPipelineState)  # pyright: ignore[reportMissingTypeArgument]

    graph.add_node("classify", _classify_node)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node("generate_questions", _generate_questions_node)  # pyright: ignore[reportUnknownMemberType]

    graph.set_entry_point("classify")  # pyright: ignore[reportUnknownMemberType]
    graph.add_conditional_edges("classify", _route_after_classify)  # pyright: ignore[reportUnknownMemberType]
    graph.add_edge("generate_questions", END)  # pyright: ignore[reportUnknownMemberType]

    return graph
