from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.domains.ai.nodes.classify import classify_goal
from app.domains.ai.nodes.questions import (
    generate_follow_up_questions as _generate_follow_ups,
)
from app.domains.ai.nodes.questions import (
    generate_questions as _generate_questions,
)
from app.domains.ai.schemas import ClassificationOutput, QuestionItem

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
    """Run the full classify → generate questions pipeline with retries.

    Returns a result object with classification, questions, or rejection info.
    """
    # Step 1: Classify the goal
    classification: ClassificationOutput = await _retry_async(classify_goal, raw_input)

    # Step 2: Check confidence threshold
    if classification.confidence < settings.ai_confidence_threshold:
        return ClassifyAndGenerateResult(
            classification=classification,
            questions=[],
            is_rejected=True,
            rejection_reason=classification.rejection_reason
            or "This goal is too vague to create a meaningful plan.",
            refinement_suggestions=classification.refinement_suggestions,
        )

    # Step 3: Generate questions
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
    """Generate follow-up questions based on initial answers, with retries.

    Returns a list of follow-up questions (may be empty if no follow-ups needed).
    """
    try:
        follow_ups: list[QuestionItem] = await _retry_async(
            _generate_follow_ups,
            raw_input,
            classification,
            questions,
            answers,
        )
    except AIOutputError:
        # If follow-up generation fails, treat it as no follow-ups needed
        logger.warning("Follow-up generation failed, proceeding without follow-ups")
        return []

    return follow_ups
