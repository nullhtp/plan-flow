from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.ai.schemas import BoardGenerationOutput, ClassificationOutput
from app.domains.ai.service import AIOutputError, generate_board_from_context
from app.domains.boards.models import Board, BoardColumn, Subtask, Task
from app.domains.goals.models import Goal, GoalStatus

logger = logging.getLogger(__name__)

# ── Fractional Indexing Utilities ────────────────────────

# Character set for fractional index keys
# (matches the JS `fractional-indexing` library).
_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE = len(_DIGITS)


def _midpoint(a: str, b: str | None) -> str:
    """Return a string lexicographically between *a* and *b*.

    If *b* is None, return a string after *a*.
    Both *a* and *b* must use characters from ``_DIGITS`` and *a* < *b*.
    """
    if b is not None and a >= b:
        msg = f"a ({a!r}) must be less than b ({b!r})"
        raise ValueError(msg)

    if b is None:
        # Append a middle character
        return a + _DIGITS[_BASE // 2]

    # Find the first index where a and b differ
    n = max(len(a), len(b))
    a_padded = a.ljust(n, _DIGITS[0])
    b_padded = b.ljust(n, _DIGITS[0])

    common_prefix = []
    for i in range(n):
        if a_padded[i] == b_padded[i]:
            common_prefix.append(a_padded[i])
        else:
            break

    prefix = "".join(common_prefix)
    idx = len(prefix)
    a_digit = _DIGITS.index(a_padded[idx]) if idx < len(a_padded) else 0
    b_digit = _DIGITS.index(b_padded[idx]) if idx < len(b_padded) else _BASE

    if b_digit - a_digit > 1:
        mid = (a_digit + b_digit) // 2
        return prefix + _DIGITS[mid]

    # Digits are adjacent — need to go deeper
    result = prefix + _DIGITS[a_digit]
    # Now find midpoint between remaining suffix of a and the ceiling
    rest_a = a_padded[idx + 1 :] if idx + 1 < len(a_padded) else ""
    return result + _midpoint_after(rest_a)


def _midpoint_after(s: str) -> str:
    """Return a suffix that sorts after *s*."""
    if not s:
        return _DIGITS[_BASE // 2]

    last_idx = _DIGITS.index(s[-1])
    if last_idx < _BASE - 1:
        return s[:-1] + _DIGITS[(last_idx + _BASE) // 2]

    # Last char is max — recurse on prefix
    return s + _DIGITS[_BASE // 2]


def generate_position_between(before: str | None, after: str | None) -> str:
    """Generate a fractional index key between two existing keys.

    - Both None → return a middle-of-range key.
    - ``before`` is None → return a key before ``after``.
    - ``after`` is None → return a key after ``before``.
    """
    if before is None and after is None:
        return "a" + _DIGITS[_BASE // 2]

    if before is None:
        assert after is not None
        # Return something before `after`
        first = _DIGITS.index(after[0]) if after else _BASE // 2
        if first > 0:
            return _DIGITS[first // 2] + _DIGITS[_BASE // 2]
        return _midpoint("", after)

    if after is None:
        return _midpoint(before, None)

    return _midpoint(before, after)


def generate_position_after(last: str | None) -> str:
    """Generate a position key that sorts after *last* (or a first key if None)."""
    return generate_position_between(last, None)


def int_to_fractional(n: int) -> str:
    """Convert an integer position (0-based) to a fractional index string."""
    if n < _BASE:
        return f"a{_DIGITS[n]}"
    return f"b{n:04d}"


# ── Error Classes ────────────────────────────────────────


class BoardNotFoundError(Exception):
    """Raised when a board is not found or not owned by the user."""


class BoardAlreadyExistsError(Exception):
    """Raised when a board already exists for the given goal."""


class GoalNotReadyError(Exception):
    """Raised when a goal is not in 'answered' status for board generation."""


class ColumnNotFoundError(Exception):
    """Raised when a column is not found or not owned by the user."""


class TaskNotFoundError(Exception):
    """Raised when a task is not found or not owned by the user."""


class SubtaskNotFoundError(Exception):
    """Raised when a subtask is not found or not owned by the user."""


class ColumnNotEmptyError(Exception):
    """Raised when deleting a column with tasks and no target."""


# ── Ownership Validation ─────────────────────────────────


async def _validate_board_ownership(
    session: AsyncSession, board_id: str, user_id: str
) -> Board:
    """Return board if it belongs to user, else raise BoardNotFoundError."""
    board = await session.get(Board, board_id)
    if board is None:
        raise BoardNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError
    return board


async def _validate_column_ownership(
    session: AsyncSession, column_id: str, user_id: str
) -> BoardColumn:
    """Return column if it belongs to user, else raise ColumnNotFoundError."""
    column = await session.get(BoardColumn, column_id)
    if column is None:
        raise ColumnNotFoundError
    board = await session.get(Board, column.board_id)
    if board is None:
        raise ColumnNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise ColumnNotFoundError
    return column


async def _validate_task_ownership(
    session: AsyncSession, task_id: str, user_id: str
) -> Task:
    """Return task if it belongs to user, else raise TaskNotFoundError."""
    task = await session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError
    column = await session.get(BoardColumn, task.column_id)
    if column is None:
        raise TaskNotFoundError
    board = await session.get(Board, column.board_id)
    if board is None:
        raise TaskNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise TaskNotFoundError
    return task


async def _validate_subtask_ownership(
    session: AsyncSession, subtask_id: str, user_id: str
) -> Subtask:
    """Return subtask if it belongs to user, else raise SubtaskNotFoundError."""
    subtask = await session.get(Subtask, subtask_id)
    if subtask is None:
        raise SubtaskNotFoundError
    task = await session.get(Task, subtask.task_id)
    if task is None:
        raise SubtaskNotFoundError
    column = await session.get(BoardColumn, task.column_id)
    if column is None:
        raise SubtaskNotFoundError
    board = await session.get(Board, column.board_id)
    if board is None:
        raise SubtaskNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise SubtaskNotFoundError
    return subtask


# ── Board Operations ─────────────────────────────────────


async def list_boards(
    session: AsyncSession,
    user_id: str,
) -> list[dict[str, Any]]:
    """Return all boards for a user with summary stats."""
    # Get all goals for user that have boards
    stmt = (
        select(
            Board.id,
            Board.goal_id,
            Board.title,
            Board.created_at,
            Goal.title.label("goal_title"),
        )
        .join(Goal, Board.goal_id == Goal.id)
        .where(Goal.user_id == user_id)
        .order_by(Board.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    boards = []
    for row in rows:
        # Count columns
        col_count_stmt = (
            select(func.count())
            .select_from(BoardColumn)
            .where(BoardColumn.board_id == row.id)
        )
        col_count_result = await session.execute(col_count_stmt)
        column_count = col_count_result.scalar() or 0

        # Count tasks
        task_count_stmt = (
            select(func.count())
            .select_from(Task)
            .join(BoardColumn, Task.column_id == BoardColumn.id)
            .where(BoardColumn.board_id == row.id)
        )
        task_count_result = await session.execute(task_count_stmt)
        task_count = task_count_result.scalar() or 0

        # Count tasks in the last column (approximation of "completed")
        last_col_stmt = (
            select(BoardColumn.id)
            .where(BoardColumn.board_id == row.id)
            .order_by(BoardColumn.position.desc())
            .limit(1)
        )
        last_col_result = await session.execute(last_col_stmt)
        last_col_id = last_col_result.scalar()
        completed_count = 0
        if last_col_id:
            completed_stmt = (
                select(func.count())
                .select_from(Task)
                .where(Task.column_id == last_col_id)
            )
            completed_result = await session.execute(completed_stmt)
            completed_count = completed_result.scalar() or 0

        boards.append(
            {
                "id": row.id,
                "goal_id": row.goal_id,
                "title": row.title,
                "goal_title": row.goal_title,
                "column_count": column_count,
                "task_count": task_count,
                "completed_task_count": completed_count,
                "created_at": row.created_at,
            }
        )

    return boards


async def update_board(
    session: AsyncSession,
    board_id: str,
    user_id: str,
    title: str,
) -> Board:
    """Update board title."""
    board = await _validate_board_ownership(session, board_id, user_id)
    board.title = title
    board.updated_at = datetime.now(UTC)
    session.add(board)
    await session.commit()
    return await get_board(session, board_id, user_id)


# ── Column Operations ────────────────────────────────────


async def create_column(
    session: AsyncSession,
    board_id: str,
    user_id: str,
    title: str,
    description: str = "",
) -> Board:
    """Create a new column at the end of the board. Returns refreshed board."""
    await _validate_board_ownership(session, board_id, user_id)

    # Find the last column's position
    stmt = (
        select(BoardColumn.position)
        .where(BoardColumn.board_id == board_id)
        .order_by(BoardColumn.position.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    last_pos = result.scalar()

    new_pos = generate_position_after(last_pos)

    column = BoardColumn(
        board_id=board_id,
        title=title,
        description=description,
        position=new_pos,
    )
    session.add(column)
    await session.commit()
    return await get_board(session, board_id, user_id)


async def update_column(
    session: AsyncSession,
    column_id: str,
    user_id: str,
    title: str | None = None,
    description: str | None = None,
    position: str | None = None,
) -> Board:
    """Update a column's title, description, or position. Returns refreshed board."""
    column = await _validate_column_ownership(session, column_id, user_id)

    if title is not None:
        column.title = title
    if description is not None:
        column.description = description
    if position is not None:
        column.position = position

    column.updated_at = datetime.now(UTC)
    session.add(column)
    await session.commit()
    return await get_board(session, column.board_id, user_id)


async def delete_column(
    session: AsyncSession,
    column_id: str,
    user_id: str,
    target_column_id: str | None = None,
) -> Board:
    """Delete a column. If it has tasks, migrate them to target_column_id."""
    column = await _validate_column_ownership(session, column_id, user_id)
    board_id = column.board_id

    # Check if column has tasks
    task_count_stmt = (
        select(func.count()).select_from(Task).where(Task.column_id == column_id)
    )
    task_count_result = await session.execute(task_count_stmt)
    task_count = task_count_result.scalar() or 0

    if task_count > 0:
        if target_column_id is None:
            raise ColumnNotEmptyError
        # Validate target column belongs to same board
        target = await session.get(BoardColumn, target_column_id)
        if target is None or target.board_id != board_id:
            raise ColumnNotFoundError

        # Find last position in target column
        last_pos_stmt = (
            select(Task.position)
            .where(Task.column_id == target_column_id)
            .order_by(Task.position.desc())
            .limit(1)
        )
        last_pos_result = await session.execute(last_pos_stmt)
        last_pos = last_pos_result.scalar()

        # Get tasks from the column being deleted, ordered by position
        tasks_stmt = (
            select(Task).where(Task.column_id == column_id).order_by(Task.position)
        )
        tasks_result = await session.execute(tasks_stmt)
        tasks_to_move = tasks_result.scalars().all()

        # Move each task to the target column with new positions
        current_pos = last_pos
        for task in tasks_to_move:
            new_pos = generate_position_after(current_pos)
            task.column_id = target_column_id
            task.position = new_pos
            task.updated_at = datetime.now(UTC)
            session.add(task)
            current_pos = new_pos

    # Delete the column (tasks have been moved or column is empty)
    await session.delete(column)
    await session.commit()
    return await get_board(session, board_id, user_id)


# ── Task Operations ──────────────────────────────────────


async def create_task(
    session: AsyncSession,
    column_id: str,
    user_id: str,
    title: str,
    description: str = "",
    due_date: date | None = None,
    priority: str | None = None,
    estimated_minutes: int | None = None,
) -> Board:
    """Create a new task at the end of the column. Returns refreshed board."""
    column = await _validate_column_ownership(session, column_id, user_id)

    # Find last task position
    stmt = (
        select(Task.position)
        .where(Task.column_id == column_id)
        .order_by(Task.position.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    last_pos = result.scalar()

    new_pos = generate_position_after(last_pos)

    task = Task(
        column_id=column_id,
        title=title,
        description=description,
        position=new_pos,
        due_date=due_date,
        priority=priority,
        estimated_minutes=estimated_minutes,
    )
    session.add(task)
    await session.commit()
    return await get_board(session, column.board_id, user_id)


async def update_task(
    session: AsyncSession,
    task_id: str,
    user_id: str,
    title: str | None = None,
    description: str | None = None,
    position: str | None = None,
    column_id: str | None = None,
    due_date: date | None = None,
    priority: str | None = None,
    estimated_minutes: int | None = None,
    _unset_due_date: bool = False,
    _unset_priority: bool = False,
    _unset_estimated_minutes: bool = False,
) -> Board:
    """Update task fields. Moves task if column_id given."""
    task = await _validate_task_ownership(session, task_id, user_id)

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if position is not None:
        task.position = position
    if column_id is not None:
        # Validate target column ownership
        await _validate_column_ownership(session, column_id, user_id)
        task.column_id = column_id
    if due_date is not None:
        task.due_date = due_date  # pyright: ignore[reportAttributeAccessIssue]
    if priority is not None:
        task.priority = priority
    if estimated_minutes is not None:
        task.estimated_minutes = estimated_minutes

    task.updated_at = datetime.now(UTC)
    session.add(task)
    await session.commit()

    # Get board_id through column
    col = await session.get(BoardColumn, task.column_id)
    assert col is not None
    return await get_board(session, col.board_id, user_id)


async def delete_task(
    session: AsyncSession,
    task_id: str,
    user_id: str,
) -> Board:
    """Delete a task and its subtasks. Returns refreshed board."""
    task = await _validate_task_ownership(session, task_id, user_id)
    column = await session.get(BoardColumn, task.column_id)
    assert column is not None
    board_id = column.board_id

    # Delete subtasks first
    await session.execute(delete(Subtask).where(Subtask.task_id == task_id))
    await session.delete(task)
    await session.commit()
    return await get_board(session, board_id, user_id)


# ── Subtask Operations ───────────────────────────────────


async def create_subtask(
    session: AsyncSession,
    task_id: str,
    user_id: str,
    title: str,
) -> Board:
    """Create a subtask at end of task's list."""
    task = await _validate_task_ownership(session, task_id, user_id)

    # Find last subtask position
    stmt = (
        select(Subtask.position)
        .where(Subtask.task_id == task_id)
        .order_by(Subtask.position.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    last_pos = result.scalar()

    new_pos = generate_position_after(last_pos)

    subtask = Subtask(
        task_id=task_id,
        title=title,
        position=new_pos,
    )
    session.add(subtask)
    await session.commit()

    column = await session.get(BoardColumn, task.column_id)
    assert column is not None
    return await get_board(session, column.board_id, user_id)


async def update_subtask(
    session: AsyncSession,
    subtask_id: str,
    user_id: str,
    title: str | None = None,
    completed: bool | None = None,
    position: str | None = None,
) -> Board:
    """Update a subtask. Returns refreshed board."""
    subtask = await _validate_subtask_ownership(session, subtask_id, user_id)

    if title is not None:
        subtask.title = title
    if completed is not None:
        subtask.completed = completed
    if position is not None:
        subtask.position = position

    subtask.updated_at = datetime.now(UTC)
    session.add(subtask)
    await session.commit()

    task = await session.get(Task, subtask.task_id)
    assert task is not None
    column = await session.get(BoardColumn, task.column_id)
    assert column is not None
    return await get_board(session, column.board_id, user_id)


async def delete_subtask(
    session: AsyncSession,
    subtask_id: str,
    user_id: str,
) -> Board:
    """Delete a subtask. Returns refreshed board."""
    subtask = await _validate_subtask_ownership(session, subtask_id, user_id)

    task = await session.get(Task, subtask.task_id)
    assert task is not None
    column = await session.get(BoardColumn, task.column_id)
    assert column is not None
    board_id = column.board_id

    await session.delete(subtask)
    await session.commit()
    return await get_board(session, board_id, user_id)


# ── Board Retrieval & AI Generation ─────────────────────


async def create_board_from_ai_output(
    session: AsyncSession,
    goal_id: str,
    ai_output: BoardGenerationOutput,
) -> Board:
    """Persist AI-generated board output as Board, Column, and Task records.

    Creates all records in a single transaction.
    Uses fractional indexing for positions.
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
            position=int_to_fractional(col_output.position),
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
                position=int_to_fractional(task_output.position),
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
    """Retrieve a board with nested data, validating ownership."""
    stmt = (
        select(Board)
        .options(
            selectinload(Board.columns)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            .selectinload(BoardColumn.tasks)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            .selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
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
            selectinload(Board.columns)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            .selectinload(BoardColumn.tasks)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            .selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
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
