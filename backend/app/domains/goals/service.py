from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.prompts.meta import format_user_meta_block
from app.domains.ai.schemas import ClassificationOutput, QuestionItem
from app.domains.ai.service import (
    AIOutputError,
    ClassifyAndGenerateResult,
    classify_and_generate_questions,
    generate_follow_up_questions,
)
from app.domains.goals.models import Goal, GoalStatus
from app.domains.goals.schemas import UserMeta


class GoalNotFoundError(Exception):
    """Raised when a goal is not found or not owned by the user."""


class GoalStatusError(Exception):
    """Raised when a goal is in the wrong status for the requested operation."""


async def create_goal(
    session: AsyncSession,
    user_id: str,
    original_input: str,
    user_meta: UserMeta | None = None,
    client_ip: str | None = None,
) -> tuple[Goal, ClassifyAndGenerateResult]:
    """Create a goal, run AI classification + question generation.

    Returns the Goal record and the AI pipeline result.
    Raises AIOutputError if the AI pipeline fails after retries.
    """
    # Build initial ai_context with user_meta if provided
    ai_context: dict[str, Any] = {}
    if user_meta is not None:
        meta_dict = user_meta.model_dump()
        # Override current_datetime with server UTC time
        meta_dict["current_datetime"] = datetime.now(UTC).isoformat()
        # Store client IP for potential geolocation fallback
        if client_ip:
            meta_dict["client_ip"] = client_ip
        ai_context["user_meta"] = meta_dict

    # Create goal record
    goal = Goal(
        user_id=user_id,
        original_input=original_input,
        status=GoalStatus.CLASSIFYING.value,
        ai_context=ai_context if ai_context else {},
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    # Format user meta for AI prompt injection
    user_context = format_user_meta_block(ai_context.get("user_meta"))

    # Run AI pipeline
    try:
        result = await classify_and_generate_questions(original_input, user_context)
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
    # Merge user_meta into ai_context alongside classification and questions
    updated_ai_context: dict[str, Any] = (
        dict(goal.ai_context) if goal.ai_context else {}
    )
    updated_ai_context["classification"] = result.classification.model_dump()
    updated_ai_context["questions"] = [q.model_dump() for q in result.questions]
    goal.ai_context = updated_ai_context
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

        # Format user meta for follow-up prompt injection
        user_context_for_follow_up = format_user_meta_block(ai_context.get("user_meta"))

        follow_ups = await generate_follow_up_questions(
            goal.original_input,
            classification,
            questions,
            answers,
            user_context_for_follow_up,
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
