from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.prompts.meta import format_user_meta_block, resolve_user_context
from app.domains.ai.schemas import ClassificationOutput, QuestionItem, QuestionsOutput
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


# ── Backward Compatibility ───────────────────────────────


def convert_legacy_ai_context(ai_context: dict[str, Any]) -> dict[str, Any]:
    """Convert old flat ai_context to rounds-based format.

    Old format had top-level keys: questions, answers,
    follow_up_questions, follow_up_answers.
    New format uses ai_context["rounds"] as an ordered list
    of {round, questions, answers, readiness} dicts.
    """
    if "rounds" in ai_context:
        return ai_context  # Already new format

    if "questions" not in ai_context:
        return ai_context  # No questions yet, nothing to convert

    rounds: list[dict[str, Any]] = []

    # Round 1: initial questions + answers
    questions = ai_context.get("questions", [])
    answers = ai_context.get("answers", {})
    rounds.append(
        {
            "round": 1,
            "questions": questions,
            "answers": answers,
            "readiness": {
                "score": 0.0,
                "covered_dimensions": [],
                "uncovered_dimensions": [],
                "summary": "",
            },
        }
    )

    # Round 2: follow-up questions + answers (if any)
    follow_up_questions = ai_context.get("follow_up_questions", [])
    if follow_up_questions:
        follow_up_answers = ai_context.get("follow_up_answers", {})
        rounds.append(
            {
                "round": 2,
                "questions": follow_up_questions,
                "answers": follow_up_answers,
                "readiness": {
                    "score": 0.0,
                    "covered_dimensions": [],
                    "uncovered_dimensions": [],
                    "summary": "",
                },
            }
        )

    # Build new context, preserving classification, user_meta, etc.
    new_context: dict[str, Any] = {}
    for key in ("classification", "user_meta"):
        if key in ai_context:
            new_context[key] = ai_context[key]
    new_context["rounds"] = rounds

    return new_context


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
    # Use resolve_user_context for classification (fresh server-side date)
    user_context = resolve_user_context(ai_context.get("user_meta"))

    # Retrieve memory context if memory is enabled
    memory_context = ""
    from app.domains.ai.memory_toggle import is_memory_enabled

    if await is_memory_enabled(session, user_id):
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
    # Build rounds-based ai_context
    updated_ai_context: dict[str, Any] = (
        dict(goal.ai_context) if goal.ai_context else {}
    )
    updated_ai_context["classification"] = result.classification.model_dump()
    # Store round 1 with questions, empty answers, initial readiness
    readiness_data = (
        result.readiness.model_dump()
        if result.readiness
        else {
            "score": 0.0,
            "covered_dimensions": [],
            "uncovered_dimensions": result.classification.dimensions,
            "summary": "No answers collected yet.",
        }
    )
    updated_ai_context["rounds"] = [
        {
            "round": 1,
            "questions": [q.model_dump() for q in result.questions],
            "answers": {},
            "readiness": readiness_data,
        }
    ]
    goal.ai_context = updated_ai_context
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    # Extract memories from classification (non-blocking best-effort)
    if await is_memory_enabled(session, user_id):
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
) -> tuple[Goal, list[QuestionItem], QuestionsOutput | None]:
    """Submit answers for a goal's questions.

    Returns (goal, next_questions, questions_output_with_readiness).
    The goal stays in 'questioning' status — no 'answered' transition.
    """
    goal = await _get_goal_for_user(session, goal_id, user_id)

    if goal.status != GoalStatus.QUESTIONING.value:
        msg = f"Goal is in '{goal.status}' status, expected 'questioning'"
        raise GoalStatusError(msg)

    from app.domains.ai.memory_toggle import is_memory_enabled

    ai_context: dict[str, Any] = dict(goal.ai_context)

    # Ensure rounds format (backward compat)
    ai_context = convert_legacy_ai_context(ai_context)

    rounds: list[dict[str, Any]] = ai_context.get("rounds", [])

    # Truncate rounds after current round if editing earlier round
    if round_num <= len(rounds):
        # Keep only rounds up to and including the current one
        rounds = rounds[:round_num]
        # Store answers on the current round
        rounds[round_num - 1]["answers"] = answers
    else:
        # This shouldn't normally happen, but handle gracefully
        if rounds:
            rounds[-1]["answers"] = answers

    ai_context["rounds"] = rounds

    # Build classification for follow-up generation
    classification_data = ai_context.get("classification", {})
    classification = ClassificationOutput.model_validate(classification_data)

    # Get questions for memory extraction
    current_round = rounds[round_num - 1] if round_num <= len(rounds) else None
    current_questions = [
        QuestionItem.model_validate(q)
        for q in (current_round.get("questions", []) if current_round else [])
    ]

    # Format user meta for follow-up prompt injection
    user_context_for_follow_up = format_user_meta_block(ai_context.get("user_meta"))

    # Retrieve memory context for follow-up questions
    memory_context_for_follow_up = ""

    if await is_memory_enabled(session, user_id):
        from app.domains.ai.memory import retrieve_relevant_memories
        from app.domains.ai.prompts.memory import format_memory_block

        memories = await retrieve_relevant_memories(
            session, user_id, goal.original_input
        )
        memory_context_for_follow_up = format_memory_block(memories)

    # Generate follow-up questions for next round
    next_round_num = round_num + 1
    follow_up_output = await generate_follow_up_questions(
        goal.original_input,
        classification,
        rounds,
        next_round_num,
        user_context_for_follow_up,
        memory_context_for_follow_up,
    )

    # Extract memories from answers (best-effort)
    if await is_memory_enabled(session, user_id):
        try:
            from app.domains.ai.memory import (
                extract_memories_from_answers,
                store_memories_batch,
            )

            mem_inputs = extract_memories_from_answers(
                current_questions, answers, goal_id
            )
            if mem_inputs:
                await store_memories_batch(
                    session, user_id, mem_inputs, source_goal_id=goal_id
                )
                await session.commit()
        except Exception:
            logger.exception("Memory extraction after answers failed")

    # Append next round with generated questions
    next_questions: list[QuestionItem] = []
    if follow_up_output and follow_up_output.questions:
        next_questions = follow_up_output.questions
        # Ensure question IDs have proper round prefix
        for i, q in enumerate(next_questions):
            expected_prefix = f"r{next_round_num}q"
            if not q.id.startswith(expected_prefix):
                q.id = f"r{next_round_num}q{i + 1}"

        readiness_data = follow_up_output.readiness.model_dump()
        rounds.append(
            {
                "round": next_round_num,
                "questions": [q.model_dump() for q in next_questions],
                "answers": {},
                "readiness": readiness_data,
            }
        )
        ai_context["rounds"] = rounds

    # Persist updated ai_context — goal stays in 'questioning'
    goal.ai_context = ai_context
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    return goal, next_questions, follow_up_output


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


async def revert_goal_to_questioning(
    session: AsyncSession,
    goal: Goal,
) -> None:
    """Revert goal status back to 'questioning' on generation failure."""
    goal.status = GoalStatus.QUESTIONING.value
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()


# Backward-compatible alias
revert_goal_to_answered = revert_goal_to_questioning
