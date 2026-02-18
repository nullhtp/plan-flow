from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.ai.prompts.meta import format_user_meta_block
from app.domains.ai.schemas import ClassificationOutput, QuestionItem
from app.domains.ai.service import (
    AIOutputError,
    ClassifyAndGenerateResult,
    classify_and_generate_questions,
    generate_follow_up_questions,
)
from app.domains.goals.models import Goal, GoalStatus
from app.domains.goals.repository import GoalRepository
from app.domains.goals.schemas import UserMeta

logger = logging.getLogger(__name__)


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

    # Retrieve memory context if memory is enabled
    memory_context = ""
    if settings.ai_memory_enabled:
        from app.domains.ai.memory import retrieve_relevant_memories
        from app.domains.ai.prompts.memory import format_memory_block

        memories = await retrieve_relevant_memories(session, user_id, original_input)
        memory_context = format_memory_block(memories)

    # Run AI pipeline
    try:
        result = await classify_and_generate_questions(
            original_input, user_context, memory_context
        )
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

    # Extract memories from classification (non-blocking best-effort)
    if settings.ai_memory_enabled:
        try:
            from app.domains.ai.memory import (
                extract_memories_from_classification,
                store_memories_batch,
            )

            mem_inputs = extract_memories_from_classification(
                result.classification, goal.id
            )
            if mem_inputs:
                await store_memories_batch(
                    session, user_id, mem_inputs, source_goal_id=goal.id
                )
                await session.commit()
        except Exception:
            logger.exception("Memory extraction after classification failed")

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

        # Retrieve memory context for follow-up questions
        memory_context_for_follow_up = ""
        if settings.ai_memory_enabled:
            from app.domains.ai.memory import retrieve_relevant_memories
            from app.domains.ai.prompts.memory import format_memory_block

            memories = await retrieve_relevant_memories(
                session, user_id, goal.original_input
            )
            memory_context_for_follow_up = format_memory_block(memories)

        follow_ups = await generate_follow_up_questions(
            goal.original_input,
            classification,
            questions,
            answers,
            user_context_for_follow_up,
            memory_context_for_follow_up,
        )

        # Extract memories from initial answers (best-effort)
        if settings.ai_memory_enabled:
            try:
                from app.domains.ai.memory import (
                    extract_memories_from_answers,
                    store_memories_batch,
                )

                mem_inputs = extract_memories_from_answers(questions, answers, goal_id)
                if mem_inputs:
                    await store_memories_batch(
                        session, user_id, mem_inputs, source_goal_id=goal_id
                    )
                    await session.commit()
            except Exception:
                logger.exception("Memory extraction after answers failed")

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

    # Extract memories from follow-up answers (best-effort)
    if settings.ai_memory_enabled:
        try:
            from app.domains.ai.memory import (
                extract_memories_from_answers,
                store_memories_batch,
            )

            follow_up_questions_data = ai_context.get("follow_up_questions", [])
            fq_list = [QuestionItem.model_validate(q) for q in follow_up_questions_data]
            mem_inputs = extract_memories_from_answers(fq_list, answers, goal_id)
            if mem_inputs:
                await store_memories_batch(
                    session, user_id, mem_inputs, source_goal_id=goal_id
                )
                await session.commit()
        except Exception:
            logger.exception("Memory extraction after follow-up answers failed")

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
    repo = GoalRepository(session)
    goal = await repo.get_for_user(goal_id, user_id)
    if goal is None:
        raise GoalNotFoundError
    return goal


# ── Goal State Transitions ───────────────────────────────


async def transition_goal_to_generating(
    session: AsyncSession,
    goal: Goal,
) -> None:
    """Transition goal status to 'generating'."""
    goal.status = GoalStatus.GENERATING.value
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)


async def transition_goal_to_active(
    session: AsyncSession,
    goal: Goal,
) -> None:
    """Transition goal status to 'active'."""
    goal.status = GoalStatus.ACTIVE.value
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)


async def revert_goal_to_answered(
    session: AsyncSession,
    goal: Goal,
) -> None:
    """Revert goal status back to 'answered' on generation failure."""
    goal.status = GoalStatus.ANSWERED.value
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
