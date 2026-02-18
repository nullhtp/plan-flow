"""Task mutation tools for AI chat.

Non-status field edits execute immediately. Status changes and subtask deletion
require user confirmation via PendingAction.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.tools._pending import create_pending_action
from app.domains.boards.models import Subtask, Task
from app.domains.boards.position_utils import generate_position_after
from app.domains.boards.task_service import are_dependencies_met

logger = logging.getLogger(__name__)


def make_update_task_field(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create an update_task_field tool (executes immediately)."""

    @tool
    async def update_task_field(task_id: str, field: str, value: str) -> dict[str, Any]:
        """Update a non-status field on a task.

        Allowed fields: title, description, due_date,
        priority, estimated_minutes.

        Args:
            task_id: The UUID of the task to update.
            field: The field name to update.
            value: The new value as a string.
        """
        allowed = {
            "title",
            "description",
            "due_date",
            "priority",
            "estimated_minutes",
        }
        if field not in allowed:
            fields = ", ".join(sorted(allowed))
            return {
                "status": "failed",
                "error": f"Field '{field}' not allowed. Use one of: {fields}",
            }

        task = await db.get(Task, task_id)
        if task is None or task.board_id != board_id:
            return {"status": "failed", "error": "Task not found on this board"}

        try:
            if field == "title":
                task.title = value
            elif field == "description":
                task.description = value
            elif field == "due_date":
                task.due_date = date.fromisoformat(value)  # pyright: ignore[reportAttributeAccessIssue]
            elif field == "priority":
                if value not in ("low", "medium", "high"):
                    return {
                        "status": "failed",
                        "error": "Priority must be low, medium, or high",
                    }
                task.priority = value
            elif field == "estimated_minutes":
                task.estimated_minutes = int(value)

            task.updated_at = datetime.now(UTC)
            db.add(task)
            await db.commit()

            return {
                "status": "executed",
                "description": f"Updated {field} on task '{task.title}'",
                "task_id": task.id,
                "field": field,
                "new_value": value,
            }
        except (ValueError, TypeError) as e:
            await db.rollback()
            return {"status": "failed", "error": f"Invalid value for {field}: {e}"}
        except Exception:
            await db.rollback()
            logger.exception("Failed to update task field")
            return {
                "status": "failed",
                "error": "Unable to update task. Please try again.",
            }

    return update_task_field


def make_update_task_status(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create an update_task_status tool (requires confirmation)."""

    @tool
    async def update_task_status(task_id: str, new_status: str) -> dict[str, Any]:
        """Change a task's status. Requires user confirmation.

        Valid statuses: not_started, in_progress, done.

        Args:
            task_id: The UUID of the task.
            new_status: The target status (not_started, in_progress, done).
        """
        valid = {"not_started", "in_progress", "done"}
        if new_status not in valid:
            return {
                "status": "failed",
                "error": f"Invalid status. Must be one of: {', '.join(sorted(valid))}",
            }

        task = await db.get(Task, task_id)
        if task is None or task.board_id != board_id:
            return {"status": "failed", "error": "Task not found on this board"}

        # Pre-validate the transition
        if task.status == "not_started" and new_status == "in_progress":
            deps_met = await are_dependencies_met(db, task.id)
            if not deps_met:
                return {
                    "status": "failed",
                    "error": "Cannot start task: not all dependencies are completed",
                }
        elif task.status == "not_started" and new_status == "done":
            return {
                "status": "failed",
                "error": "Cannot complete task directly: must be in progress first",
            }

        # Create pending action for confirmation
        action = await create_pending_action(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            tool_name="update_task_status",
            tool_args={"task_id": task_id, "new_status": new_status},
            description=(
                f"Change status of '{task.title}' "
                f"from '{task.status}' to '{new_status}'"
            ),
        )

        desc = f"Change status of '{task.title}' from '{task.status}' to '{new_status}'"
        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "description": desc,
        }

    return update_task_status


def make_create_subtask(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create a create_subtask tool (executes immediately)."""

    @tool
    async def create_subtask(task_id: str, title: str) -> dict[str, Any]:
        """Create a new subtask on a task. Executes immediately.

        Args:
            task_id: The UUID of the parent task.
            title: The title of the new subtask.
        """
        task = await db.get(Task, task_id)
        if task is None or task.board_id != board_id:
            return {"status": "failed", "error": "Task not found on this board"}

        try:
            from sqlalchemy import select as sa_select

            stmt = (
                sa_select(Subtask.position)
                .where(Subtask.task_id == task_id)  # pyright: ignore[reportArgumentType]
                .order_by(Subtask.position.desc())  # pyright: ignore[reportAttributeAccessIssue]
                .limit(1)
            )
            result = await db.execute(stmt)
            last_pos = result.scalar()
            new_pos = generate_position_after(last_pos)

            subtask = Subtask(
                task_id=task_id,
                title=title,
                position=new_pos,
            )
            db.add(subtask)
            await db.commit()

            return {
                "status": "executed",
                "description": f"Created subtask '{title}' on task '{task.title}'",
                "subtask_id": subtask.id,
                "title": title,
            }
        except Exception:
            await db.rollback()
            logger.exception("Failed to create subtask")
            return {
                "status": "failed",
                "error": "Unable to create subtask. Please try again.",
            }

    return create_subtask


def make_toggle_subtask(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create a toggle_subtask tool (executes immediately)."""

    @tool
    async def toggle_subtask(subtask_id: str) -> dict[str, Any]:
        """Toggle a subtask's completed status. Executes immediately.

        Args:
            subtask_id: The UUID of the subtask to toggle.
        """
        subtask = await db.get(Subtask, subtask_id)
        if subtask is None:
            return {"status": "failed", "error": "Subtask not found"}

        task = await db.get(Task, subtask.task_id)
        if task is None or task.board_id != board_id:
            return {"status": "failed", "error": "Subtask not found on this board"}

        try:
            subtask.completed = not subtask.completed
            subtask.updated_at = datetime.now(UTC)
            db.add(subtask)
            await db.commit()

            status_text = "completed" if subtask.completed else "uncompleted"
            return {
                "status": "executed",
                "description": f"Marked subtask '{subtask.title}' as {status_text}",
                "subtask_id": subtask.id,
                "completed": subtask.completed,
            }
        except Exception:
            await db.rollback()
            logger.exception("Failed to toggle subtask")
            return {
                "status": "failed",
                "error": "Unable to toggle subtask. Please try again.",
            }

    return toggle_subtask


def make_delete_subtask(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create a delete_subtask tool (requires confirmation)."""

    @tool
    async def delete_subtask(subtask_id: str) -> dict[str, Any]:
        """Delete a subtask. Requires user confirmation.

        Args:
            subtask_id: The UUID of the subtask to delete.
        """
        subtask = await db.get(Subtask, subtask_id)
        if subtask is None:
            return {"status": "failed", "error": "Subtask not found"}

        task = await db.get(Task, subtask.task_id)
        if task is None or task.board_id != board_id:
            return {"status": "failed", "error": "Subtask not found on this board"}

        action = await create_pending_action(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            tool_name="delete_subtask",
            tool_args={"subtask_id": subtask_id},
            description=f"Delete subtask '{subtask.title}' from task '{task.title}'",
        )

        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "description": f"Delete subtask '{subtask.title}' from task '{task.title}'",
        }

    return delete_subtask
