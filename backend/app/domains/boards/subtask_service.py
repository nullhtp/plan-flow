"""Subtask-level operations: CRUD + automatic task-status sync."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Board, Subtask, Task
from app.domains.boards.ownership import (
    validate_subtask_ownership,
    validate_task_ownership,
)
from app.domains.boards.position_utils import generate_position_after
from app.domains.boards.subtask_repository import SubtaskRepository
from app.domains.boards.task_repository import TaskRepository


async def sync_task_status_from_subtasks(session: AsyncSession, task: Task) -> None:
    """Automatically transition task status based on subtask completion.

    Rules:
    - Any subtask completed and task is ``not_started`` → ``in_progress``
      (only if dependencies are met).
    - All subtasks completed and task is ``in_progress`` → ``done``.
    - Any subtask incomplete and task is ``done`` → ``in_progress``.

    This intentionally bypasses :func:`_validate_status_transition` because
    the transition is a derived side-effect, not a user-initiated action.
    """
    # Fetch subtask completion counts for this task
    rows = (
        await session.execute(
            select(Subtask.completed).where(Subtask.task_id == task.id)
        )
    ).all()
    total = len(rows)
    completed = sum(1 for (c,) in rows if c)

    if total == 0:
        return

    old_status = task.status
    new_status = old_status

    if completed > 0 and old_status == "not_started":
        # A subtask was checked — auto-start, but only if deps are met
        repo = TaskRepository(session)
        if await repo.are_dependencies_met(task.id):
            new_status = "in_progress"
    elif completed == total and old_status == "in_progress":
        new_status = "done"
    elif completed < total and old_status == "done":
        new_status = "in_progress"

    if new_status != old_status:
        task.status = new_status
        task.updated_at = datetime.now(UTC)
        session.add(task)


async def create_subtask(
    session: AsyncSession,
    task_id: str,
    user_id: str,
    title: str,
) -> Board:
    """Create a subtask at end of task's list."""
    task = await validate_task_ownership(session, task_id, user_id)

    repo = SubtaskRepository(session)
    last_pos = await repo.get_last_position(task_id)
    new_pos = generate_position_after(last_pos)

    subtask = Subtask(
        task_id=task_id,
        title=title,
        position=new_pos,
    )
    await repo.create(subtask)
    await session.commit()

    from app.domains.boards.board_service import get_board

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
    subtask = await validate_subtask_ownership(session, subtask_id, user_id)

    if title is not None:
        subtask.title = title
    if completed is not None:
        subtask.completed = completed
    if position is not None:
        subtask.position = position

    subtask.updated_at = datetime.now(UTC)
    repo = SubtaskRepository(session)
    await repo.update(subtask)

    # Auto-sync parent task status when subtask completion changes
    if completed is not None:
        task = await session.get(Task, subtask.task_id)
        assert task is not None
        await sync_task_status_from_subtasks(session, task)

    await session.commit()

    task = await session.get(Task, subtask.task_id)
    assert task is not None

    from app.domains.boards.board_service import get_board

    return await get_board(session, task.board_id, user_id)


async def delete_subtask(
    session: AsyncSession,
    subtask_id: str,
    user_id: str,
) -> Board:
    """Delete a subtask. Returns refreshed board."""
    subtask = await validate_subtask_ownership(session, subtask_id, user_id)

    task = await session.get(Task, subtask.task_id)
    assert task is not None
    board_id = task.board_id

    repo = SubtaskRepository(session)
    await repo.delete(subtask)

    # Re-sync task status after subtask removal
    await sync_task_status_from_subtasks(session, task)

    await session.commit()

    from app.domains.boards.board_service import get_board

    return await get_board(session, board_id, user_id)
