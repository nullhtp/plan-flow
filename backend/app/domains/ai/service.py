from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.domains.ai.nodes.classify import classify_goal
from app.domains.ai.nodes.generate_board import generate_board as _generate_board
from app.domains.ai.nodes.questions import (
    generate_follow_up_questions as _generate_follow_ups,
)
from app.domains.ai.nodes.questions import (
    generate_questions as _generate_questions,
)
from app.domains.ai.schemas import (
    BoardGenerationOutput,
    ClassificationOutput,
    QuestionItem,
)
from app.domains.boards.dag_utils import (
    CyclicDependencyError,
    GoalNodeValidationError,
    validate_dag,
    validate_goal_node,
)

logger = logging.getLogger(__name__)


class AIOutputError(Exception):
    """Raised when the AI produces invalid output after all retries."""


@dataclass
class ClassifyAndGenerateResult:
    """Result of the classify-and-generate pipeline."""

    classification: ClassificationOutput
    questions: list[QuestionItem]
    is_rejected: bool
    rejection_reason: str | None = None
    refinement_suggestions: list[str] | None = None


async def _retry_async(
    fn: Any,
    *args: Any,
    max_retries: int = settings.ai_max_retries,
) -> Any:
    """Retry an async function up to max_retries times on validation errors."""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await fn(*args)
        except (ValidationError, TypeError) as e:
            last_error = e
            logger.warning(
                "AI output validation failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )
    msg = f"AI output validation failed after {max_retries} attempts"
    raise AIOutputError(msg) from last_error


async def classify_and_generate_questions(
    raw_input: str,
) -> ClassifyAndGenerateResult:
    """Run the full classify -> generate questions pipeline with retries."""
    classification: ClassificationOutput = await _retry_async(classify_goal, raw_input)

    if classification.confidence < settings.ai_confidence_threshold:
        return ClassifyAndGenerateResult(
            classification=classification,
            questions=[],
            is_rejected=True,
            rejection_reason=classification.rejection_reason
            or "This goal is too vague to create a meaningful plan.",
            refinement_suggestions=classification.refinement_suggestions,
        )

    questions: list[QuestionItem] = await _retry_async(
        _generate_questions, raw_input, classification
    )

    return ClassifyAndGenerateResult(
        classification=classification,
        questions=questions,
        is_rejected=False,
    )


async def generate_follow_up_questions(
    raw_input: str,
    classification: ClassificationOutput,
    questions: list[QuestionItem],
    answers: dict[str, Any],
) -> list[QuestionItem]:
    """Generate follow-up questions based on initial answers, with retries."""
    try:
        follow_ups: list[QuestionItem] = await _retry_async(
            _generate_follow_ups,
            raw_input,
            classification,
            questions,
            answers,
        )
    except AIOutputError:
        logger.warning("Follow-up generation failed, proceeding without follow-ups")
        return []

    return follow_ups


def _validate_board_dag(output: BoardGenerationOutput) -> None:
    """Validate that AI board output forms a valid DAG.

    Raises CyclicDependencyError or GoalNodeValidationError on failure.
    """
    task_ids = [t.id for t in output.tasks]
    goal_flags = {t.id: t.is_goal_node for t in output.tasks}
    edges: list[tuple[str, str]] = []
    for t in output.tasks:
        for dep_id in t.depends_on:
            if dep_id in set(task_ids):
                edges.append((dep_id, t.id))

    validate_dag(task_ids, edges)
    validate_goal_node(task_ids, goal_flags, edges)


async def generate_board_from_context(
    raw_input: str,
    domain: str,
    complexity: int,
    dimensions: list[str],
    qa_pairs: str,
) -> BoardGenerationOutput:
    """Generate a board from goal context, with retries.

    Returns a BoardGenerationOutput with tasks and dependency edges.
    Raises AIOutputError if the AI fails after all retries.
    Retries on cyclic dependency graphs (counts toward retry limit).
    """
    max_retries = settings.ai_max_retries
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            result: BoardGenerationOutput = await _generate_board(
                raw_input, domain, complexity, dimensions, qa_pairs
            )
            # Validate DAG structure
            _validate_board_dag(result)
            return result
        except (ValidationError, TypeError) as e:
            last_error = e
            logger.warning(
                "AI board generation validation failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )
        except (CyclicDependencyError, GoalNodeValidationError) as e:
            last_error = e
            logger.warning(
                "AI generated invalid DAG (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                str(e),
            )

    msg = f"AI board generation failed after {max_retries} attempts"
    raise AIOutputError(msg) from last_error
