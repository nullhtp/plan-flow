"""Read-only information retrieval tools for AI chat.

These tools execute immediately without user confirmation.
Each tool factory accepts context (board_id, db_session, user_id) and returns
a bound LangChain tool via closure.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Board, Task


def make_get_task_details(db: AsyncSession, board_id: str, user_id: str) -> Any:
    """Create a get_task_details tool bound to the given context."""

    @tool
    async def get_task_details(task_id: str) -> dict[str, Any]:
        """Get full details of a specific task including subtasks and dependencies.

        Args:
            task_id: The UUID of the task to retrieve.
        """
        task = await db.get(Task, task_id)
        if task is None or task.board_id != board_id:
            return {"error": "Task not found on this board"}

        # Gather subtasks
        subtasks = [
            {"id": s.id, "title": s.title, "completed": s.completed}
            for s in task.subtasks
        ]

        # Gather dependency info
        dep_ids = [d.dependency_task_id for d in task.dependencies]
        dependent_ids = [d.dependent_task_id for d in task.dependents]

        # Resolve dependency titles
        dep_titles: list[str] = []
        for d in task.dependencies:
            if d.dependency_task is not None:
                dep_titles.append(d.dependency_task.title)

        dependent_titles: list[str] = []
        for d in task.dependents:
            if d.dependent_task is not None:
                dependent_titles.append(d.dependent_task.title)

        # Compute is_locked
        is_locked = False
        board = await db.get(Board, board_id)
        if board is not None:
            for dep_edge in task.dependencies:
                for t in board.tasks:
                    if t.id == dep_edge.dependency_task_id and t.status != "done":
                        is_locked = True
                        break
                if is_locked:
                    break

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "is_goal_node": task.is_goal_node,
            "is_locked": is_locked,
            "priority": task.priority,
            "due_date": str(task.due_date) if task.due_date else None,
            "estimated_minutes": task.estimated_minutes,
            "subtasks": subtasks,
            "dependency_ids": dep_ids,
            "dependency_titles": dep_titles,
            "dependent_ids": dependent_ids,
            "dependent_titles": dependent_titles,
        }

    return get_task_details


def make_get_board_overview(db: AsyncSession, board_id: str, user_id: str) -> Any:
    """Create a get_board_overview tool bound to the given context."""

    @tool
    async def get_board_overview() -> dict[str, Any]:
        """Get a high-level overview of the board: title, task counts by status."""
        board = await db.get(Board, board_id)
        if board is None:
            return {"error": "Board not found"}

        total = len(board.tasks)
        done = sum(1 for t in board.tasks if t.status == "done")
        in_progress = sum(1 for t in board.tasks if t.status == "in_progress")
        not_started = sum(1 for t in board.tasks if t.status == "not_started")
        blocked = 0
        for t in board.tasks:
            for dep_edge in t.dependencies:
                for other in board.tasks:
                    if (
                        other.id == dep_edge.dependency_task_id
                        and other.status != "done"
                    ):
                        blocked += 1
                        break
                else:
                    continue
                break

        return {
            "board_title": board.title,
            "total_tasks": total,
            "done": done,
            "in_progress": in_progress,
            "not_started": not_started,
            "blocked": blocked,
        }

    return get_board_overview


def make_get_blocked_tasks(db: AsyncSession, board_id: str, user_id: str) -> Any:
    """Create a get_blocked_tasks tool bound to the given context."""

    @tool
    async def get_blocked_tasks() -> list[dict[str, Any]]:
        """List all tasks that are currently locked (have unmet dependencies)."""
        board = await db.get(Board, board_id)
        if board is None:
            return [{"error": "Board not found"}]

        result: list[dict[str, Any]] = []
        for t in board.tasks:
            if t.status == "done":
                continue
            blocking: list[str] = []
            for dep_edge in t.dependencies:
                for other in board.tasks:
                    if (
                        other.id == dep_edge.dependency_task_id
                        and other.status != "done"
                    ):
                        blocking.append(other.title)
                        break
            if blocking:
                result.append(
                    {
                        "task_id": t.id,
                        "task_title": t.title,
                        "blocked_by": blocking,
                    }
                )
        return result

    return get_blocked_tasks


def make_get_task_dependencies(db: AsyncSession, board_id: str, user_id: str) -> Any:
    """Create a get_task_dependencies tool bound to the given context."""

    @tool
    async def get_task_dependencies(task_id: str) -> dict[str, Any]:
        """Get the prerequisite and dependent tasks for a specific task.

        Args:
            task_id: The UUID of the task.
        """
        task = await db.get(Task, task_id)
        if task is None or task.board_id != board_id:
            return {"error": "Task not found on this board"}

        prerequisites = []
        for d in task.dependencies:
            if d.dependency_task is not None:
                prerequisites.append(
                    {
                        "id": d.dependency_task.id,
                        "title": d.dependency_task.title,
                        "status": d.dependency_task.status,
                    }
                )

        dependents = []
        for d in task.dependents:
            if d.dependent_task is not None:
                dependents.append(
                    {
                        "id": d.dependent_task.id,
                        "title": d.dependent_task.title,
                        "status": d.dependent_task.status,
                    }
                )

        return {
            "task_title": task.title,
            "prerequisites": prerequisites,
            "dependents": dependents,
        }

    return get_task_dependencies


def make_list_all_tasks(db: AsyncSession, board_id: str, user_id: str) -> Any:
    """Create a list_all_tasks tool bound to the given context."""

    @tool
    async def list_all_tasks() -> list[dict[str, Any]]:
        """List all tasks on the board with their status and key info."""
        board = await db.get(Board, board_id)
        if board is None:
            return [{"error": "Board not found"}]

        result: list[dict[str, Any]] = []
        for t in board.tasks:
            # Compute is_locked
            is_locked = False
            for dep_edge in t.dependencies:
                for other in board.tasks:
                    if (
                        other.id == dep_edge.dependency_task_id
                        and other.status != "done"
                    ):
                        is_locked = True
                        break
                if is_locked:
                    break

            result.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "is_locked": is_locked,
                    "is_goal_node": t.is_goal_node,
                    "priority": t.priority,
                }
            )
        return result

    return list_all_tasks


def make_get_board_progress(db: AsyncSession, board_id: str, user_id: str) -> Any:
    """Create a get_board_progress tool bound to the given context."""

    @tool
    async def get_board_progress() -> dict[str, Any]:
        """Get progress stats: completion %, status counts, time."""
        board = await db.get(Board, board_id)
        if board is None:
            return {"error": "Board not found"}

        total = len(board.tasks)
        done = sum(1 for t in board.tasks if t.status == "done")
        in_progress = sum(1 for t in board.tasks if t.status == "in_progress")
        not_started = sum(1 for t in board.tasks if t.status == "not_started")

        completion_pct = round((done / total * 100) if total > 0 else 0, 1)

        # Sum estimated_minutes for incomplete tasks
        remaining_minutes = sum(
            t.estimated_minutes or 0 for t in board.tasks if t.status != "done"
        )

        return {
            "total_tasks": total,
            "done": done,
            "in_progress": in_progress,
            "not_started": not_started,
            "completion_percentage": completion_pct,
            "estimated_minutes_remaining": remaining_minutes,
        }

    return get_board_progress
