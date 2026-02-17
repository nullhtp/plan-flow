"""Unit tests for AI retrieval tools.

These tests use the test database (via conftest fixtures) since tools
operate on real SQLAlchemy models with selectin-loaded relationships.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.tools.retrieval import (
    make_get_blocked_tasks,
    make_get_board_overview,
    make_get_board_progress,
    make_get_task_dependencies,
    make_get_task_details,
    make_list_all_tasks,
)
from app.domains.auth.models import User
from app.domains.boards.models import Board
from app.domains.goals.models import Goal
from tests.conftest import create_test_board


@pytest.fixture
async def board_with_tasks(
    session: AsyncSession, test_user: User, answered_goal: Goal
) -> tuple[Board, dict[str, str]]:
    """Create a test board with the standard 3-task DAG."""
    return await create_test_board(session, answered_goal)


# ── get_task_details ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_task_details_success(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Returns full details for a valid task on the board."""
    board, id_map = board_with_tasks
    task_id = id_map["t1"]

    tool = make_get_task_details(session, board.id, test_user.id)
    result = await tool.ainvoke({"task_id": task_id})

    assert result["id"] == task_id
    assert result["title"] == "Task 1"
    assert result["status"] == "not_started"
    assert "subtasks" in result
    assert "dependency_ids" in result


@pytest.mark.asyncio
async def test_get_task_details_not_found(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Returns error for a non-existent task."""
    board, _ = board_with_tasks

    tool = make_get_task_details(session, board.id, test_user.id)
    result = await tool.ainvoke({"task_id": "nonexistent-id"})

    assert "error" in result


@pytest.mark.asyncio
async def test_get_task_details_goal_task_dependencies(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Goal task (t3) shows t1 and t2 as dependencies."""
    board, id_map = board_with_tasks
    goal_task_id = id_map["t3"]

    tool = make_get_task_details(session, board.id, test_user.id)
    result = await tool.ainvoke({"task_id": goal_task_id})

    assert result["is_goal_node"] is True
    assert len(result["dependency_ids"]) == 2
    assert result["is_locked"] is True  # t1, t2 are not_started


# ── get_board_overview ───────────────────────────────────


@pytest.mark.asyncio
async def test_get_board_overview(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Returns correct counts for the standard 3-task board."""
    board, _ = board_with_tasks

    tool = make_get_board_overview(session, board.id, test_user.id)
    result = await tool.ainvoke({})

    assert result["total_tasks"] == 3
    assert result["not_started"] == 3
    assert result["done"] == 0
    assert result["in_progress"] == 0


@pytest.mark.asyncio
async def test_get_board_overview_not_found(
    session: AsyncSession, test_user: User
) -> None:
    """Returns error for non-existent board."""
    tool = make_get_board_overview(session, "nonexistent-board", test_user.id)
    result = await tool.ainvoke({})
    assert "error" in result


# ── get_blocked_tasks ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_blocked_tasks(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Goal task (t3) is blocked by t1 and t2."""
    board, id_map = board_with_tasks

    tool = make_get_blocked_tasks(session, board.id, test_user.id)
    result = await tool.ainvoke({})

    # t3 depends on t1 and t2 which are both not_started
    blocked_ids = {item["task_id"] for item in result}
    assert id_map["t3"] in blocked_ids


# ── get_task_dependencies ────────────────────────────────


@pytest.mark.asyncio
async def test_get_task_dependencies_with_deps(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Goal task shows its prerequisites."""
    board, id_map = board_with_tasks
    goal_task_id = id_map["t3"]

    tool = make_get_task_dependencies(session, board.id, test_user.id)
    result = await tool.ainvoke({"task_id": goal_task_id})

    assert result["task_title"] == "Goal Task"
    assert len(result["prerequisites"]) == 2
    assert len(result["dependents"]) == 0


@pytest.mark.asyncio
async def test_get_task_dependencies_no_deps(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Root task t1 has no prerequisites but has dependents."""
    board, id_map = board_with_tasks
    task_id = id_map["t1"]

    tool = make_get_task_dependencies(session, board.id, test_user.id)
    result = await tool.ainvoke({"task_id": task_id})

    assert result["task_title"] == "Task 1"
    assert len(result["prerequisites"]) == 0
    assert len(result["dependents"]) == 1  # t3


# ── list_all_tasks ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_all_tasks(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Returns all 3 tasks with correct info."""
    board, _ = board_with_tasks

    tool = make_list_all_tasks(session, board.id, test_user.id)
    result = await tool.ainvoke({})

    assert len(result) == 3
    titles = {t["title"] for t in result}
    assert titles == {"Task 1", "Task 2", "Goal Task"}


# ── get_board_progress ───────────────────────────────────


@pytest.mark.asyncio
async def test_get_board_progress(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Returns correct progress stats with 0% completion."""
    board, _ = board_with_tasks

    tool = make_get_board_progress(session, board.id, test_user.id)
    result = await tool.ainvoke({})

    assert result["total_tasks"] == 3
    assert result["completion_percentage"] == 0.0
    assert result["done"] == 0
