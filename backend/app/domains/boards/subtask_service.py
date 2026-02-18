"""Subtask-level operations: CRUD."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Board, Subtask, Task
from app.domains.boards.ownership import (
    validate_subtask_ownership,
    validate_task_ownership,
)
from app.domains.boards.position_utils import generate_position_after
from app.domains.boards.subtask_repository import SubtaskRepository


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
    await session.commit()

    from app.domains.boards.board_service import get_board

    return await get_board(session, board_id, user_id)
