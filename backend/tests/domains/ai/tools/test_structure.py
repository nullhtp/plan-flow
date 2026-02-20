"""Unit tests for AI structure tools.

Tests verify DAG validation, goal node protection, and confirmation flow.

NOTE: We call tool.coroutine(...) directly instead of tool.ainvoke(...)
because LangChain's Runnable wrapper breaks SQLAlchemy's async greenlet
context when used inside pytest-asyncio tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import PendingAction
from app.domains.ai.tools.structure import (
    make_add_dependency,
    make_add_task,
    make_remove_dependency,
    make_remove_task,
    make_split_task,
)
from app.domains.auth.models import User
from app.domains.boards.models import Board
from app.domains.goals.models import Goal
from tests.conftest import create_test_board


@pytest.fixture
async def board_with_tasks(
    session: AsyncSession, test_user: User, answered_goal: Goal
) -> tuple[Board, dict[str, str]]:
    return await create_test_board(session, answered_goal)


THREAD_ID = "test-thread-structure"


# ── add_task ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_task_creates_pending_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, _id_map = board_with_tasks

    tool = make_add_task(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(title="New Task", description="A new task")

    assert result["status"] == "pending_confirmation"
    assert "pending_action_id" in result

    action = await session.get(PendingAction, result["pending_action_id"])
    assert action is not None
    assert action.tool_name == "add_task"


@pytest.mark.asyncio
async def test_add_task_with_cycle_rejected(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Adding a task that creates a cycle is rejected."""
    board, id_map = board_with_tasks

    # t3 depends on t1 and t2. If new task depends on t3 and t1 depends on new task,
    # that's a cycle: t1 -> t3 -> new -> t1
    tool = make_add_task(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(
        title="Cycle Task",
        depends_on_ids=[id_map["t3"]],
        dependent_ids=[id_map["t1"]],
    )

    assert result["status"] == "failed"
    assert "cycle" in result["error"].lower()


# ── remove_task ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_task_creates_pending_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_remove_task(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(task_id=id_map["t1"])

    assert result["status"] == "pending_confirmation"


@pytest.mark.asyncio
async def test_remove_goal_node_rejected(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Cannot remove the goal node."""
    board, id_map = board_with_tasks

    tool = make_remove_task(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(task_id=id_map["t3"])

    assert result["status"] == "failed"
    assert "goal node" in result["error"].lower()


# ── add_dependency ───────────────────────────────────────


@pytest.mark.asyncio
async def test_add_dependency_creates_pending_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Adding t1 -> t2 dependency (t2 depends on t1) creates a pending action."""
    board, id_map = board_with_tasks

    tool = make_add_dependency(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(
        dependent_task_id=id_map["t2"],
        dependency_task_id=id_map["t1"],
    )

    assert result["status"] == "pending_confirmation"


@pytest.mark.asyncio
async def test_add_dependency_cycle_rejected(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Adding t1 depends on t3 creates a cycle (t1 -> t3 -> t1)."""
    board, id_map = board_with_tasks

    tool = make_add_dependency(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(
        dependent_task_id=id_map["t1"],
        dependency_task_id=id_map["t3"],
    )

    assert result["status"] == "failed"
    assert "cycle" in result["error"].lower()


# ── remove_dependency ────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_dependency_creates_pending_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Removing an existing dependency creates a pending action."""
    board, id_map = board_with_tasks

    tool = make_remove_dependency(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(
        dependent_task_id=id_map["t3"],
        dependency_task_id=id_map["t1"],
    )

    assert result["status"] == "pending_confirmation"


# ── split_task ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_split_task_creates_pending_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_split_task(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(
        task_id=id_map["t1"],
        new_tasks=[
            {"title": "Task 1a", "description": "First part"},
            {"title": "Task 1b", "description": "Second part"},
        ],
    )

    assert result["status"] == "pending_confirmation"


@pytest.mark.asyncio
async def test_split_goal_node_rejected(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_split_task(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(
        task_id=id_map["t3"],
        new_tasks=[
            {"title": "Part A"},
            {"title": "Part B"},
        ],
    )

    assert result["status"] == "failed"
    assert "goal node" in result["error"].lower()


@pytest.mark.asyncio
async def test_split_task_too_few_rejected(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_split_task(session, board.id, test_user.id, THREAD_ID)
    result = await tool.coroutine(
        task_id=id_map["t1"],
        new_tasks=[{"title": "Only one"}],
    )

    assert result["status"] == "failed"
    assert "at least 2" in result["error"]
