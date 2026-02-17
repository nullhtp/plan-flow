from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.ai.schemas import (
    BoardSkeletonOutput,
    TaskEnrichmentOutput,
)
from app.domains.boards.dag_utils import (
    validate_dag,
    validate_goal_node,
)
from app.domains.boards.models import Board, Subtask, Task, TaskDependency
from app.domains.boards.schemas import BoardResponse, EdgeResponse, TaskResponse
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
    """Generate a fractional index key between two existing keys."""
    if before is None and after is None:
        return "a" + _DIGITS[_BASE // 2]

    if before is None:
        assert after is not None
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


# ── Error Classes ────────────────────────────────────────


class BoardNotFoundError(Exception):
    """Raised when a board is not found or not owned by the user."""


class BoardAlreadyExistsError(Exception):
    """Raised when a board already exists for the given goal."""


class GoalNotReadyError(Exception):
    """Raised when a goal is not in 'answered' status for board generation."""


class TaskNotFoundError(Exception):
    """Raised when a task is not found or not owned by the user."""


class SubtaskNotFoundError(Exception):
    """Raised when a subtask is not found or not owned by the user."""


class TaskStatusError(Exception):
    """Raised when a task status transition is invalid."""


class DependencyError(Exception):
    """Raised when dependency constraints are violated."""


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


async def _validate_task_ownership(
    session: AsyncSession, task_id: str, user_id: str
) -> Task:
    """Return task if it belongs to user, else raise TaskNotFoundError."""
    task = await session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError
    board = await session.get(Board, task.board_id)
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
    board = await session.get(Board, task.board_id)
    if board is None:
        raise SubtaskNotFoundError
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise SubtaskNotFoundError
    return subtask


# ── Dependency Query Helpers ────────────────────────────


async def get_task_dependencies(session: AsyncSession, task_id: str) -> list[Task]:
    """Return all prerequisite tasks for a given task."""
    stmt = (
        select(Task)
        .join(TaskDependency, TaskDependency.dependency_task_id == Task.id)
        .where(TaskDependency.dependent_task_id == task_id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_task_dependents(session: AsyncSession, task_id: str) -> list[Task]:
    """Return all tasks that depend on the given task."""
    stmt = (
        select(Task)
        .join(TaskDependency, TaskDependency.dependent_task_id == Task.id)
        .where(TaskDependency.dependency_task_id == task_id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def are_dependencies_met(session: AsyncSession, task_id: str) -> bool:
    """Check if all prerequisite tasks have status 'done'."""
    stmt = (
        select(func.count())
        .select_from(TaskDependency)
        .join(Task, TaskDependency.dependency_task_id == Task.id)
        .where(
            TaskDependency.dependent_task_id == task_id,
            Task.status != "done",
        )
    )
    result = await session.execute(stmt)
    unmet_count = result.scalar() or 0
    return unmet_count == 0


# ── Board Operations ─────────────────────────────────────


async def list_boards(
    session: AsyncSession,
    user_id: str,
) -> list[dict[str, Any]]:
    """Return all boards for a user with summary stats."""
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
        # Count total tasks
        task_count_stmt = (
            select(func.count()).select_from(Task).where(Task.board_id == row.id)
        )
        task_count_result = await session.execute(task_count_stmt)
        task_count = task_count_result.scalar() or 0

        # Count completed tasks (status = 'done')
        completed_stmt = (
            select(func.count())
            .select_from(Task)
            .where(Task.board_id == row.id, Task.status == "done")
        )
        completed_result = await session.execute(completed_stmt)
        completed_count = completed_result.scalar() or 0

        boards.append(
            {
                "id": row.id,
                "goal_id": row.goal_id,
                "title": row.title,
                "goal_title": row.goal_title,
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


# ── Task Operations ──────────────────────────────────────


async def create_task(
    session: AsyncSession,
    board_id: str,
    user_id: str,
    title: str,
    description: str = "",
    due_date: date | None = None,
    priority: str | None = None,
    estimated_minutes: int | None = None,
) -> Board:
    """Create a new task on a board. Returns refreshed board."""
    await _validate_board_ownership(session, board_id, user_id)

    task = Task(
        board_id=board_id,
        title=title,
        description=description,
        status="not_started",
        due_date=due_date,
        priority=priority,
        estimated_minutes=estimated_minutes,
    )
    session.add(task)
    await session.commit()
    return await get_board(session, board_id, user_id)


async def update_task(
    session: AsyncSession,
    task_id: str,
    user_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    due_date: date | None = None,
    priority: str | None = None,
    estimated_minutes: int | None = None,
) -> Board:
    """Update task fields. Validates status transitions."""
    task = await _validate_task_ownership(session, task_id, user_id)

    if status is not None and status != task.status:
        await _validate_status_transition(session, task, status)
        task.status = status

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if due_date is not None:
        task.due_date = due_date  # pyright: ignore[reportAttributeAccessIssue]
    if priority is not None:
        task.priority = priority
    if estimated_minutes is not None:
        task.estimated_minutes = estimated_minutes

    task.updated_at = datetime.now(UTC)
    session.add(task)
    await session.commit()

    return await get_board(session, task.board_id, user_id)


async def _validate_status_transition(
    session: AsyncSession, task: Task, new_status: str
) -> None:
    """Validate a task status transition.

    Rules:
    - not_started -> in_progress: requires all deps done
    - in_progress -> done: allowed
    - not_started -> done: rejected
    - done -> not_started/in_progress: allowed (undo)
    """
    valid_statuses = {"not_started", "in_progress", "done"}
    if new_status not in valid_statuses:
        raise TaskStatusError(f"Invalid status: {new_status}")

    if task.status == "not_started" and new_status == "in_progress":
        deps_met = await are_dependencies_met(session, task.id)
        if not deps_met:
            raise TaskStatusError(
                "Cannot start task: not all dependencies are completed"
            )
    elif task.status == "not_started" and new_status == "done":
        raise TaskStatusError(
            "Cannot complete task directly: must be in progress first"
        )
    elif task.status == "in_progress" and new_status == "done":
        pass  # Always allowed
    elif task.status == "done" and new_status in ("not_started", "in_progress"):
        pass  # Allow undo


async def delete_task(
    session: AsyncSession,
    task_id: str,
    user_id: str,
) -> Board:
    """Delete a task, its subtasks, and all dependency edges. Returns refreshed board."""  # noqa: E501
    task = await _validate_task_ownership(session, task_id, user_id)
    board_id = task.board_id

    # Delete subtasks
    await session.execute(delete(Subtask).where(Subtask.task_id == task_id))
    # Delete dependency edges (both as dependent and as dependency)
    await session.execute(
        delete(TaskDependency).where(TaskDependency.dependent_task_id == task_id)
    )
    await session.execute(
        delete(TaskDependency).where(TaskDependency.dependency_task_id == task_id)
    )
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

    return await get_board(session, task.board_id, user_id)


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
    return await get_board(session, task.board_id, user_id)


async def delete_subtask(
    session: AsyncSession,
    subtask_id: str,
    user_id: str,
) -> Board:
    """Delete a subtask. Returns refreshed board."""
    subtask = await _validate_subtask_ownership(session, subtask_id, user_id)

    task = await session.get(Task, subtask.task_id)
    assert task is not None
    board_id = task.board_id

    await session.delete(subtask)
    await session.commit()
    return await get_board(session, board_id, user_id)


# ── Board Retrieval & AI Generation ─────────────────────


async def create_board_from_skeleton(
    session: AsyncSession,
    goal_id: str,
    skeleton: BoardSkeletonOutput,
) -> tuple[Board, dict[str, str]]:
    """Persist skeleton as Board + Task (empty descriptions) + TaskDependency records.

    Phase 1 of two-phase persistence. Creates all records in a single transaction.
    Returns (board, ai_id_to_db_id mapping).
    """
    board = Board(
        goal_id=goal_id,
        title=skeleton.board_title,
    )
    session.add(board)
    await session.flush()  # Get board.id without committing

    # Build mapping from AI task IDs to DB task IDs
    ai_id_to_db_id: dict[str, str] = {}
    ai_id_to_goal_flag: dict[str, bool] = {}
    edges: list[tuple[str, str]] = []

    # Create all tasks (with titles only, empty descriptions)
    for task_output in skeleton.tasks:
        task = Task(
            board_id=board.id,
            title=task_output.title,
            description="",
            status="not_started",
            is_goal_node=task_output.is_goal_node,
        )
        session.add(task)
        await session.flush()  # Get task.id

        ai_id_to_db_id[task_output.id] = task.id
        ai_id_to_goal_flag[task_output.id] = task_output.is_goal_node

    # Validate DAG structure
    all_ai_ids = list(ai_id_to_db_id.keys())
    for task_output in skeleton.tasks:
        for dep_id in task_output.depends_on:
            if dep_id in ai_id_to_db_id:
                edges.append((dep_id, task_output.id))

    # Run DAG validation
    validate_dag(all_ai_ids, edges)
    validate_goal_node(all_ai_ids, ai_id_to_goal_flag, edges)

    # Create dependency edges
    for dep_ai_id, dependent_ai_id in edges:
        dep_db_id = ai_id_to_db_id[dep_ai_id]
        dependent_db_id = ai_id_to_db_id[dependent_ai_id]
        dependency = TaskDependency(
            dependent_task_id=dependent_db_id,
            dependency_task_id=dep_db_id,
        )
        session.add(dependency)

    await session.commit()
    await session.refresh(board)
    return board, ai_id_to_db_id


async def update_task_with_enrichment(
    session: AsyncSession,
    task_id: str,
    enrichment: TaskEnrichmentOutput,
) -> list[str]:
    """Update a single Task record with enrichment data and create Subtask records.

    Phase 2 of two-phase persistence. Each call is its own transaction.
    Returns list of created subtask IDs.
    """
    task = await session.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError

    # Update task fields
    task.description = enrichment.description
    task.updated_at = datetime.now(UTC)

    if enrichment.due_date is not None:
        try:
            task.due_date = date.fromisoformat(enrichment.due_date)  # pyright: ignore[reportAttributeAccessIssue]
        except ValueError:
            logger.warning(
                "Invalid due_date '%s' for task '%s', setting to null",
                enrichment.due_date,
                task.title,
            )
    if enrichment.priority is not None:
        task.priority = enrichment.priority
    if enrichment.estimated_minutes is not None:
        task.estimated_minutes = enrichment.estimated_minutes

    session.add(task)

    # Create subtask records with fractional index positions
    subtask_ids: list[str] = []
    last_position: str | None = None
    for subtask_output in enrichment.subtasks:
        new_pos = generate_position_after(last_position)
        subtask = Subtask(
            task_id=task_id,
            title=subtask_output.title,
            position=new_pos,
        )
        session.add(subtask)
        await session.flush()
        subtask_ids.append(subtask.id)
        last_position = new_pos

    await session.commit()
    return subtask_ids


def _build_board_response(board: Board) -> BoardResponse:
    """Build a BoardResponse from a Board with loaded relationships."""
    tasks = board.tasks
    edges: list[EdgeResponse] = []
    task_responses: list[TaskResponse] = []

    # Collect all dependency info
    for task in tasks:
        dependency_ids = [d.dependency_task_id for d in task.dependencies]
        dependent_ids = [d.dependent_task_id for d in task.dependents]

        # Compute is_locked: at least one dependency is not done
        is_locked = False
        for dep_edge in task.dependencies:
            # Find the dependency task in our loaded tasks
            for t in tasks:
                if t.id == dep_edge.dependency_task_id and t.status != "done":
                    is_locked = True
                    break
            if is_locked:
                break

        task_responses.append(
            TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                is_goal_node=task.is_goal_node,
                due_date=task.due_date,
                priority=task.priority,
                estimated_minutes=task.estimated_minutes,
                subtasks=[
                    {  # type: ignore[misc]
                        "id": s.id,
                        "title": s.title,
                        "completed": s.completed,
                        "position": s.position,
                        "created_at": s.created_at,
                    }
                    for s in task.subtasks
                ],
                dependency_ids=dependency_ids,
                dependent_ids=dependent_ids,
                is_locked=is_locked,
                created_at=task.created_at,
            )
        )

        # Add edges
        for dep_edge in task.dependencies:
            edges.append(
                EdgeResponse(
                    source=dep_edge.dependency_task_id,
                    target=dep_edge.dependent_task_id,
                )
            )

    # Deduplicate edges (they may appear from both sides)
    seen_edges: set[tuple[str, str]] = set()
    unique_edges: list[EdgeResponse] = []
    for edge in edges:
        key = (edge.source, edge.target)
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)

    # Compute is_completed: goal node has status done
    is_completed = any(t.is_goal_node and t.status == "done" for t in tasks)

    return BoardResponse(
        id=board.id,
        goal_id=board.goal_id,
        title=board.title,
        tasks=task_responses,
        edges=unique_edges,
        is_completed=is_completed,
        created_at=board.created_at,
    )


async def get_board(
    session: AsyncSession,
    board_id: str,
    user_id: str,
) -> Board:
    """Retrieve a board with nested data, validating ownership."""
    # Expire all cached objects to ensure selectinload re-fetches relationships
    session.expire_all()
    stmt = (
        select(Board)
        .options(
            selectinload(Board.tasks).selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            selectinload(Board.tasks).selectinload(Task.dependencies),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            selectinload(Board.tasks).selectinload(Task.dependents),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
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
    goal = await session.get(Goal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError

    stmt = (
        select(Board)
        .options(
            selectinload(Board.tasks).selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            selectinload(Board.tasks).selectinload(Task.dependencies),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            selectinload(Board.tasks).selectinload(Task.dependents),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
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


async def validate_goal_for_generation(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
) -> Goal:
    """Validate that a goal is ready for board generation.

    Pre-flight checks that run before the SSE stream starts,
    so errors can be returned as regular HTTP responses.

    Raises GoalNotReadyError if goal is not in 'answered' status.
    Raises BoardAlreadyExistsError if a board already exists.
    Raises BoardNotFoundError if goal not found or not owned by user.
    """
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

    return goal


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
