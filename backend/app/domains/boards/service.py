from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.ai.schemas import BoardGenerationOutput, ClassificationOutput
from app.domains.ai.service import AIOutputError, generate_board_from_context
from app.domains.boards.models import Board, BoardColumn, Task
from app.domains.goals.models import Goal, GoalStatus

logger = logging.getLogger(__name__)


class BoardNotFoundError(Exception):
    """Raised when a board is not found or not owned by the user."""


class BoardAlreadyExistsError(Exception):
    """Raised when a board already exists for the given goal."""


class GoalNotReadyError(Exception):
    """Raised when a goal is not in 'answered' status for board generation."""


async def create_board_from_ai_output(
    session: AsyncSession,
    goal_id: str,
    ai_output: BoardGenerationOutput,
) -> Board:
    """Persist AI-generated board output as Board, Column, and Task records.

    Creates all records in a single transaction.
    """
    board = Board(
        goal_id=goal_id,
        title=ai_output.board_title,
    )
    session.add(board)
    await session.flush()  # Get board.id without committing

    for col_output in ai_output.columns:
        column = BoardColumn(
            board_id=board.id,
            title=col_output.title,
            description=col_output.description,
            position=col_output.position,
        )
        session.add(column)
        await session.flush()  # Get column.id

        for task_output in col_output.tasks:
            parsed_due_date: date | None = None
            if task_output.due_date is not None:
                try:
                    parsed_due_date = date.fromisoformat(task_output.due_date)
                except ValueError:
                    logger.warning(
                        "Invalid due_date '%s' for task '%s', setting to null",
                        task_output.due_date,
                        task_output.title,
                    )

            task = Task(
                column_id=column.id,
                title=task_output.title,
                description=task_output.description,
                position=task_output.position,
                due_date=parsed_due_date,
                priority=task_output.priority,
                estimated_minutes=task_output.estimated_minutes,
            )
            session.add(task)

    await session.commit()
    await session.refresh(board)
    return board


async def get_board(
    session: AsyncSession,
    board_id: str,
    user_id: str,
) -> Board:
    """Retrieve a board with nested columns and tasks, validating ownership."""
    stmt = (
        select(Board)
        .options(
            selectinload(Board.columns).selectinload(BoardColumn.tasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )
        .where(Board.id == board_id)
    )
    result = await session.execute(stmt)
    board = result.scalar_one_or_none()

    if board is None:
        raise BoardNotFoundError

    # Validate ownership via goal
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError

    return board


async def get_board_by_goal(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
) -> Board:
    """Retrieve a board by goal_id, validating ownership."""
    # First verify the goal exists and belongs to the user
    goal = await session.get(Goal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError

    stmt = (
        select(Board)
        .options(
            selectinload(Board.columns).selectinload(BoardColumn.tasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )
        .where(Board.goal_id == goal_id)
    )
    result = await session.execute(stmt)
    board = result.scalar_one_or_none()

    if board is None:
        raise BoardNotFoundError

    return board


def _format_qa_pairs(ai_context: dict[str, Any]) -> str:
    """Format questions and answers from ai_context into a string for the prompt."""
    lines: list[str] = []
    questions = ai_context.get("questions", [])
    answers = ai_context.get("answers", {})
    follow_up_questions = ai_context.get("follow_up_questions", [])
    follow_up_answers = ai_context.get("follow_up_answers", {})

    for q in questions:
        qid = q.get("id", "")
        text = q.get("text", "")
        answer = answers.get(qid, "(not answered)")
        lines.append(f"Q ({qid}): {text}\nA: {answer}")

    for q in follow_up_questions:
        qid = q.get("id", "")
        text = q.get("text", "")
        answer = follow_up_answers.get(qid, "(not answered)")
        lines.append(f"Q ({qid}): {text}\nA: {answer}")

    return "\n\n".join(lines)


async def generate_board_for_goal(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
) -> Board:
    """Full orchestration: validate goal, call AI, persist board, update status.

    Raises GoalNotReadyError if goal is not in 'answered' status.
    Raises BoardAlreadyExistsError if a board already exists.
    Raises BoardNotFoundError if goal not found or not owned by user.
    Raises AIOutputError if the AI pipeline fails.
    """
    # Validate goal
    goal = await session.get(Goal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError

    if goal.status != GoalStatus.ANSWERED.value:
        msg = f"Goal is in '{goal.status}' status, expected 'answered'"
        raise GoalNotReadyError(msg)

    # Check no board already exists
    existing_stmt = select(Board).where(Board.goal_id == goal_id)
    existing_result = await session.execute(existing_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise BoardAlreadyExistsError

    # Transition to generating
    goal.status = GoalStatus.GENERATING.value
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    # Extract context from ai_context
    ai_context: dict[str, Any] = dict(goal.ai_context)
    classification_data = ai_context.get("classification", {})
    classification = ClassificationOutput.model_validate(classification_data)
    qa_pairs = _format_qa_pairs(ai_context)

    # Call AI service
    try:
        ai_output = await generate_board_from_context(
            raw_input=goal.original_input,
            domain=classification.domain,
            complexity=classification.complexity,
            dimensions=classification.dimensions,
            qa_pairs=qa_pairs,
        )
    except AIOutputError:
        # Revert status to answered on failure
        goal.status = GoalStatus.ANSWERED.value
        goal.updated_at = datetime.now(UTC)
        session.add(goal)
        await session.commit()
        raise

    # Persist board
    board = await create_board_from_ai_output(session, goal_id, ai_output)

    # Transition to active
    goal.status = GoalStatus.ACTIVE.value
    goal.updated_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    # Re-fetch board with relationships loaded
    return await get_board(session, board.id, user_id)
