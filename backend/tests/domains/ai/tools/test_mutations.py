"""Unit tests for AI mutation tools.

Tests verify immediate execution vs. pending action creation
and business rule enforcement.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import PendingAction
from app.domains.ai.tools.mutations import (
    make_create_subtask,
    make_delete_subtask,
    make_save_artifact,
    make_toggle_subtask,
    make_update_artifact,
    make_update_task_field,
    make_update_task_status,
)
from app.domains.auth.models import User
from app.domains.boards.models import Artifact, Board, Task
from app.domains.goals.models import Goal
from tests.conftest import create_test_board


@pytest.fixture
async def board_with_tasks(
    session: AsyncSession, test_user: User, answered_goal: Goal
) -> tuple[Board, dict[str, str]]:
    return await create_test_board(session, answered_goal)


THREAD_ID = "test-thread-123"


# ── update_task_field (immediate) ────────────────────────


@pytest.mark.asyncio
async def test_update_task_field_title(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks
    task_id = id_map["t1"]

    tool = make_update_task_field(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke(
        {"task_id": task_id, "field": "title", "value": "New Title"}
    )

    assert result["status"] == "executed"
    assert result["new_value"] == "New Title"

    # Verify in DB
    task = await session.get(Task, task_id)
    assert task is not None
    assert task.title == "New Title"


@pytest.mark.asyncio
async def test_update_task_field_invalid_field(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_update_task_field(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke(
        {"task_id": id_map["t1"], "field": "status", "value": "done"}
    )

    assert result["status"] == "failed"
    assert "not allowed" in result["error"]


@pytest.mark.asyncio
async def test_update_task_field_invalid_priority(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_update_task_field(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke(
        {"task_id": id_map["t1"], "field": "priority", "value": "urgent"}
    )

    assert result["status"] == "failed"
    assert "low, medium, or high" in result["error"]


# ── update_task_status (requires confirmation) ───────────


@pytest.mark.asyncio
async def test_update_task_status_creates_pending_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke({"task_id": id_map["t1"], "new_status": "in_progress"})

    assert result["status"] == "pending_confirmation"
    assert "pending_action_id" in result

    # Verify PendingAction exists
    action = await session.get(PendingAction, result["pending_action_id"])
    assert action is not None
    assert action.tool_name == "update_task_status"
    assert action.status == "pending"


@pytest.mark.asyncio
async def test_update_task_status_invalid_status(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke({"task_id": id_map["t1"], "new_status": "completed"})

    assert result["status"] == "failed"
    assert "Invalid status" in result["error"]


@pytest.mark.asyncio
async def test_update_task_status_skip_to_done_rejected(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    """Cannot go directly from not_started to done."""
    board, id_map = board_with_tasks

    tool = make_update_task_status(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke({"task_id": id_map["t1"], "new_status": "done"})

    assert result["status"] == "failed"
    assert "must be in progress" in result["error"]


# ── create_subtask (immediate) ───────────────────────────


@pytest.mark.asyncio
async def test_create_subtask(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    tool = make_create_subtask(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke({"task_id": id_map["t1"], "title": "Sub-item 1"})

    assert result["status"] == "executed"
    assert result["title"] == "Sub-item 1"
    assert "subtask_id" in result


@pytest.mark.asyncio
async def test_create_subtask_wrong_board(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    _, id_map = board_with_tasks

    tool = make_create_subtask(session, "wrong-board-id", test_user.id, THREAD_ID)
    result = await tool.ainvoke({"task_id": id_map["t1"], "title": "Test"})

    assert result["status"] == "failed"


# ── toggle_subtask (immediate) ───────────────────────────


@pytest.mark.asyncio
async def test_toggle_subtask(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    # First create a subtask
    create_tool = make_create_subtask(session, board.id, test_user.id, THREAD_ID)
    create_result = await create_tool.ainvoke(
        {"task_id": id_map["t1"], "title": "Sub-item"}
    )
    subtask_id = create_result["subtask_id"]

    # Toggle it
    tool = make_toggle_subtask(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke({"subtask_id": subtask_id})

    assert result["status"] == "executed"
    assert result["completed"] is True

    # Toggle again
    result2 = await tool.ainvoke({"subtask_id": subtask_id})
    assert result2["completed"] is False


# ── delete_subtask (requires confirmation) ───────────────


@pytest.mark.asyncio
async def test_delete_subtask_creates_pending_action(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks

    # Create a subtask first
    create_tool = make_create_subtask(session, board.id, test_user.id, THREAD_ID)
    create_result = await create_tool.ainvoke(
        {"task_id": id_map["t1"], "title": "To Delete"}
    )
    subtask_id = create_result["subtask_id"]

    # Attempt delete
    tool = make_delete_subtask(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke({"subtask_id": subtask_id})

    assert result["status"] == "pending_confirmation"
    assert "pending_action_id" in result


# ── update_artifact (immediate) ──────────────────────────


@pytest.mark.asyncio
async def test_update_artifact_success(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks
    task_id = id_map["t1"]

    # Create an artifact first via save_artifact
    save_tool = make_save_artifact(session, board.id, task_id, test_user.id, THREAD_ID)
    save_result = await save_tool.ainvoke(
        {"title": "Original Title", "content": "# Original\nContent"}
    )
    assert save_result["status"] == "executed"
    artifact_id = save_result["artifact_id"]

    # Update it
    update_tool = make_update_artifact(session, board.id, test_user.id, THREAD_ID)
    result = await update_tool.ainvoke(
        {
            "artifact_id": artifact_id,
            "title": "Updated Title",
            "content": "# Updated\nNew content here",
        }
    )

    assert result["status"] == "executed"
    assert result["title"] == "Updated Title"

    # Verify in DB
    artifact = await session.get(Artifact, artifact_id)
    assert artifact is not None
    assert artifact.title == "Updated Title"
    assert artifact.content == "# Updated\nNew content here"


@pytest.mark.asyncio
async def test_update_artifact_not_found(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, _ = board_with_tasks

    tool = make_update_artifact(session, board.id, test_user.id, THREAD_ID)
    result = await tool.ainvoke(
        {
            "artifact_id": "nonexistent-id",
            "title": "X",
            "content": "Y",
        }
    )

    assert result["status"] == "failed"
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_update_artifact_wrong_board(
    session: AsyncSession,
    test_user: User,
    board_with_tasks: tuple[Board, dict[str, str]],
) -> None:
    board, id_map = board_with_tasks
    task_id = id_map["t1"]

    # Create an artifact on the correct board
    save_tool = make_save_artifact(session, board.id, task_id, test_user.id, THREAD_ID)
    save_result = await save_tool.ainvoke({"title": "Test", "content": "Content"})
    artifact_id = save_result["artifact_id"]

    # Try to update from wrong board
    tool = make_update_artifact(session, "wrong-board-id", test_user.id, THREAD_ID)
    result = await tool.ainvoke(
        {
            "artifact_id": artifact_id,
            "title": "Hacked",
            "content": "Bad content",
        }
    )

    assert result["status"] == "failed"
    assert "not found" in result["error"].lower()
