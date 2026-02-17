"""Unit tests for tool registry.

Tests verify correct tool sets per context and Tavily exclusion.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.tools.registry import (
    get_board_chat_tools,
    get_task_chat_tools,
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


@patch("app.domains.ai.tools.registry.make_web_search", return_value=None)
def test_task_chat_tools_without_tavily(
    mock_ws: MagicMock,
    session: AsyncSession,
) -> None:
    """Task chat returns tools without web_search when Tavily is not configured."""
    tools = get_task_chat_tools(
        db=session,
        board_id="board-1",
        task_id="task-1",
        user_id="user-1",
        thread_id="thread-1",
    )

    tool_names = {t.name for t in tools}
    assert "web_search" not in tool_names
    # Should have retrieval + mutation tools
    assert "get_task_details" in tool_names
    assert "get_board_overview" in tool_names
    assert "update_task_field" in tool_names
    assert "update_task_status" in tool_names
    assert "create_subtask" in tool_names
    assert "toggle_subtask" in tool_names
    assert "delete_subtask" in tool_names


@patch("app.domains.ai.tools.registry.make_web_search")
def test_task_chat_tools_with_tavily(
    mock_ws: MagicMock,
    session: AsyncSession,
) -> None:
    """Task chat includes web_search when Tavily is configured."""
    fake_tool = MagicMock()
    fake_tool.name = "web_search"
    mock_ws.return_value = fake_tool

    tools = get_task_chat_tools(
        db=session,
        board_id="board-1",
        task_id="task-1",
        user_id="user-1",
        thread_id="thread-1",
    )

    tool_names = {t.name for t in tools}
    assert "web_search" in tool_names


@patch("app.domains.ai.tools.registry.make_web_search", return_value=None)
def test_board_chat_tools_include_structure(
    mock_ws: MagicMock,
    session: AsyncSession,
) -> None:
    """Board chat tools include structure tools that task chat doesn't."""
    tools = get_board_chat_tools(
        db=session,
        board_id="board-1",
        user_id="user-1",
        thread_id="thread-1",
    )

    tool_names = {t.name for t in tools}
    # Board chat should have structure tools
    assert "add_task" in tool_names
    assert "remove_task" in tool_names
    assert "add_dependency" in tool_names
    assert "remove_dependency" in tool_names
    assert "split_task" in tool_names
    # And board-wide retrieval tools
    assert "list_all_tasks" in tool_names
    assert "get_board_progress" in tool_names


@patch("app.domains.ai.tools.registry.make_web_search", return_value=None)
def test_task_chat_tools_exclude_structure(
    mock_ws: MagicMock,
    session: AsyncSession,
) -> None:
    """Task chat tools do NOT include board structure tools."""
    tools = get_task_chat_tools(
        db=session,
        board_id="board-1",
        task_id="task-1",
        user_id="user-1",
        thread_id="thread-1",
    )

    tool_names = {t.name for t in tools}
    assert "add_task" not in tool_names
    assert "remove_task" not in tool_names
    assert "split_task" not in tool_names
