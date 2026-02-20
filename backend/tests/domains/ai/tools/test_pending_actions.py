"""Integration tests for confirm/reject flow.

Tests the PendingAction CRUD service and tool execution dispatcher.

NOTE: We call tool.coroutine(...) directly instead of tool.ainvoke(...)
because LangChain's Runnable wrapper breaks SQLAlchemy's async greenlet
context when used inside pytest-asyncio tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import PendingAction
from app.domains.ai.pending_actions import confirm_action, reject_action
from app.domains.ai.tools.mutations import make_update_task_status
from app.domains.auth.models import User
from app.domains.boards.models import Board, Task
from app.domains.goals.models import Goal
from tests.conftest import create_test_board


@pytest.fixture
async def board_with_tasks(
    session: AsyncSession, test_user: User, answered_goal: Goal
) -> tuple[Board, dict[str, str]]:
    return await create_test_board(session, answered_goal)


THREAD_ID = "test-thread-confirm"


# ── Happy path: confirm ──────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_status_change(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Confirming a status change executes it and updates the task."""
    board, id_map = board_with_tasks
    task_id = id_map["t1"]

    # Create a pending action for status change
    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(task_id=task_id, new_status="in_progress")

    assert result["status"] == "pending_confirmation"
    action_id = result["pending_action_id"]

    # Confirm it
    confirm_result = await confirm_action(session, action_id, test_user.id)
    assert confirm_result["status"] == "executed"

    # Verify task was updated
    task = await session.get(Task, task_id)
    assert task is not None
    assert task.status == "in_progress"

    # Verify action status
    action = await session.get(PendingAction, action_id)
    assert action is not None
    assert action.status == "confirmed"


# ── Happy path: reject ───────────────────────────────────


@pytest.mark.asyncio
async def test_reject_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Rejecting an action marks it as rejected without executing."""
    board, id_map = board_with_tasks
    task_id = id_map["t1"]

    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(task_id=task_id, new_status="in_progress")
    action_id = result["pending_action_id"]

    reject_result = await reject_action(session, action_id, test_user.id)
    assert reject_result["status"] == "rejected"

    # Task should NOT be updated
    task = await session.get(Task, task_id)
    assert task is not None
    assert task.status == "not_started"


# ── Expired action ───────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_expired_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Confirming an expired action returns 'expired' status."""
    _board, id_map = board_with_tasks

    # Create action with already-expired timestamp
    action = PendingAction(
        user_id=test_user.id,
        thread_id=THREAD_ID,
        tool_name="update_task_status",
        tool_args={"task_id": id_map["t1"], "new_status": "in_progress"},
        description="Test",
        status="pending",
        created_at=datetime.now(UTC) - timedelta(minutes=20),
        expires_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    session.add(action)
    await session.commit()
    await session.refresh(action)

    result = await confirm_action(session, action.id, test_user.id)
    assert result["status"] == "expired"


# ── Already confirmed ───────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_already_confirmed(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Confirming an already-confirmed action returns 'already_resolved'."""
    board, id_map = board_with_tasks

    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(task_id=id_map["t1"], new_status="in_progress")
    action_id = result["pending_action_id"]

    # Confirm first time
    await confirm_action(session, action_id, test_user.id)

    # Confirm second time
    result2 = await confirm_action(session, action_id, test_user.id)
    assert result2["status"] == "already_resolved"


# ── Wrong user ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_wrong_user(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Confirming an action owned by a different user returns 'not_found'."""
    board, id_map = board_with_tasks

    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(task_id=id_map["t1"], new_status="in_progress")
    action_id = result["pending_action_id"]

    # Try to confirm as different user
    result2 = await confirm_action(session, action_id, "different-user-id")
    assert result2["status"] == "not_found"


# ── Expires old pending actions ──────────────────────────


@pytest.mark.asyncio
async def test_new_pending_expires_old(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Creating a new pending action expires existing ones on the same thread."""
    board, id_map = board_with_tasks

    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)

    # Create first pending action
    r1 = await tool.coroutine(task_id=id_map["t1"], new_status="in_progress")
    action_id_1 = r1["pending_action_id"]

    # Create second pending action on same thread
    r2 = await tool.coroutine(task_id=id_map["t2"], new_status="in_progress")
    action_id_2 = r2["pending_action_id"]

    # First action should be expired
    action1 = await session.get(PendingAction, action_id_1)
    assert action1 is not None
    assert action1.status == "expired"

    # Second should still be pending
    action2 = await session.get(PendingAction, action_id_2)
    assert action2 is not None
    assert action2.status == "pending"
