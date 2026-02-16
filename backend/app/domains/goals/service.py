from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.schemas import ClassificationOutput, QuestionItem
from app.domains.ai.service import (
    AIOutputError,
    ClassifyAndGenerateResult,
    classify_and_generate_questions,
    generate_follow_up_questions,
)
from app.domains.goals.models import Goal, GoalStatus


class GoalNotFoundError(Exception):
    """Raised when a goal is not found or not owned by the user."""


class GoalStatusError(Exception):
    """Raised when a goal is in the wrong status for the requested operation."""


async def create_goal(
    session: AsyncSession,
    user_id: str,
    original_input: str,
) -> tuple[Goal, ClassifyAndGenerateResult]:
    """Create a goal, run AI classification + question generation.

    Returns the Goal record and the AI pipeline result.
    Raises AIOutputError if the AI pipeline fails after retries.
    """
    # Create goal record
    goal = Goal(
        user_id=user_id,
        original_input=original_input,
        status=GoalStatus.CLASSIFYING.value,
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    # Run AI pipeline
    try:
        result = await classify_and_generate_questions(original_input)
    except AIOutputError:
        # Reset goal status on failure
        goal.status = GoalStatus.INPUT.value
        goal.updated_at = datetime.now(UTC)
        session.add(goal)
        await session.commit()
        raise

    # Update goal with AI results
    if result.is_rejected:
        # Store classification even for rejected goals, then delete the goal
        # since rejected goals shouldn't persist
        await session.delete(goal)
        await session.commit()
        return goal, result

    goal.title = result.classification.suggested_title
    goal.status = GoalStatus.QUESTIONING.value
    goal.ai_context = {
        "classification": result.classification.model_dump(),
        "questions": [q.model_dump() for q in result.questions],
    }
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    return goal, result


async def submit_answers(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
    answers: dict[str, Any],
    round_num: int,
) -> tuple[Goal, list[QuestionItem], bool]:
    """Submit answers for a goal's questions.

    Returns (goal, follow_up_questions, is_complete).
    """
    goal = await _get_goal_for_user(session, goal_id, user_id)

    if goal.status != GoalStatus.QUESTIONING.value:
        msg = f"Goal is in '{goal.status}' status, expected 'questioning'"
        raise GoalStatusError(msg)

    ai_context: dict[str, Any] = dict(goal.ai_context)

    if round_num == 1:
        # Store initial answers
        ai_context["answers"] = answers

        # Try to generate follow-up questions
        classification_data = ai_context.get("classification", {})
        classification = ClassificationOutput.model_validate(classification_data)
        questions_data = ai_context.get("questions", [])
        questions = [QuestionItem.model_validate(q) for q in questions_data]

        follow_ups = await generate_follow_up_questions(
            goal.original_input,
            classification,
            questions,
            answers,
        )

        if follow_ups:
            ai_context["follow_up_questions"] = [q.model_dump() for q in follow_ups]
            goal.ai_context = ai_context
            goal.updated_at = datetime.now(UTC)
            session.add(goal)
            await session.commit()
            await session.refresh(goal)
            return goal, follow_ups, False

        # No follow-ups needed — mark as answered
        goal.ai_context = ai_context
        goal.status = GoalStatus.ANSWERED.value
        goal.updated_at = datetime.now(UTC)
        session.add(goal)
        await session.commit()
        await session.refresh(goal)
        return goal, [], True

    # Round 2 — always completes
    ai_context["follow_up_answers"] = answers
    goal.ai_context = ai_context
    goal.status = GoalStatus.ANSWERED.value
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal, [], True


async def get_goal(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
) -> Goal:
    """Get a goal by ID, ensuring the user owns it."""
    return await _get_goal_for_user(session, goal_id, user_id)


async def _get_goal_for_user(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
) -> Goal:
    """Fetch a goal and verify ownership."""
    goal = await session.get(Goal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise GoalNotFoundError
    return goal
