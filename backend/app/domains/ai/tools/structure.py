"""Board structure tools for AI chat.

All structure tools require user confirmation via PendingAction.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.tools._pending import create_pending_action
from app.domains.boards.dag_utils import CyclicDependencyError, validate_dag
from app.domains.boards.models import Board, Task

logger = logging.getLogger(__name__)


def make_add_task(db: AsyncSession, board_id: str, user_id: str, thread_id: str) -> Any:
    """Create an add_task tool (requires confirmation)."""

    @tool
    async def add_task(
        title: str,
        description: str = "",
        depends_on_ids: list[str] | None = None,
        dependent_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a new task to the board. Requires user confirmation.

        Args:
            title: The title of the new task.
            description: Optional description.
            depends_on_ids: Task IDs this new task depends on (prerequisites).
            dependent_ids: Task IDs that should depend on this new task.
        """
        board = await db.get(Board, board_id)
        if board is None:
            return {"status": "failed", "error": "Board not found"}

        deps = depends_on_ids or []
        dependents = dependent_ids or []

        # Validate referenced tasks exist on this board
        task_ids_on_board = {t.id for t in board.tasks}
        for tid in deps + dependents:
            if tid not in task_ids_on_board:
                return {
                    "status": "failed",
                    "error": f"Task '{tid}' not found on this board",
                }

        # Check DAG validity with the new task
        existing_ids = list(task_ids_on_board)
        new_id = "__new_task__"
        all_ids = [*existing_ids, new_id]

        # Collect existing edges
        edges: list[tuple[str, str]] = []
        for t in board.tasks:
            for d in t.dependencies:
                edges.append((d.dependency_task_id, d.dependent_task_id))

        # Add new edges
        for dep_id in deps:
            edges.append((dep_id, new_id))
        for dependent_id in dependents:
            edges.append((new_id, dependent_id))

        try:
            validate_dag(all_ids, edges)
        except CyclicDependencyError:
            return {
                "status": "failed",
                "error": "Adding this task would create a cycle "
                "in the dependency graph",
            }

        action = await create_pending_action(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            tool_name="add_task",
            tool_args={
                "board_id": board_id,
                "title": title,
                "description": description,
                "depends_on_ids": deps,
                "dependent_ids": dependents,
            },
            description=f"Add task '{title}' to the board",
        )

        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "description": f"Add task '{title}' to the board",
        }

    return add_task


def make_remove_task(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create a remove_task tool (requires confirmation)."""

    @tool
    async def remove_task(task_id: str) -> dict[str, Any]:
        """Remove a task and its dependency edges. Requires confirmation.

        Cannot remove the goal node.

        Args:
            task_id: The UUID of the task to remove.
        """
        task = await db.get(Task, task_id)
        if task is None or task.board_id != board_id:
            return {"status": "failed", "error": "Task not found on this board"}

        if task.is_goal_node:
            return {
                "status": "failed",
                "error": "Cannot remove the goal node — it represents the final goal",
            }

        action = await create_pending_action(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            tool_name="remove_task",
            tool_args={"task_id": task_id},
            description=f"Remove task '{task.title}' and all its dependency edges",
        )

        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "description": f"Remove task '{task.title}' and all its dependency edges",
        }

    return remove_task


def make_add_dependency(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create an add_dependency tool (requires confirmation)."""

    @tool
    async def add_dependency(
        dependent_task_id: str, dependency_task_id: str
    ) -> dict[str, Any]:
        """Add a dependency edge. Requires confirmation.

        The dependent_task will require dependency_task first.

        Args:
            dependent_task_id: The task that will be blocked.
            dependency_task_id: The prerequisite task.
        """
        board = await db.get(Board, board_id)
        if board is None:
            return {"status": "failed", "error": "Board not found"}

        task_ids_on_board = {t.id for t in board.tasks}
        if dependent_task_id not in task_ids_on_board:
            return {
                "status": "failed",
                "error": f"Dependent task '{dependent_task_id}' "
                "not found on this board",
            }
        if dependency_task_id not in task_ids_on_board:
            return {
                "status": "failed",
                "error": f"Dependency task '{dependency_task_id}' "
                "not found on this board",
            }

        # Check DAG validity with the new edge
        existing_ids = list(task_ids_on_board)
        edges: list[tuple[str, str]] = []
        for t in board.tasks:
            for d in t.dependencies:
                edges.append((d.dependency_task_id, d.dependent_task_id))
        edges.append((dependency_task_id, dependent_task_id))

        try:
            validate_dag(existing_ids, edges)
        except CyclicDependencyError:
            return {
                "status": "failed",
                "error": "Adding this dependency would create a cycle in the graph",
            }

        # Get task titles for description
        dep_task = await db.get(Task, dependency_task_id)
        dependent_task = await db.get(Task, dependent_task_id)
        dep_title = dep_task.title if dep_task else dependency_task_id
        dependent_title = dependent_task.title if dependent_task else dependent_task_id

        action = await create_pending_action(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            tool_name="add_dependency",
            tool_args={
                "dependent_task_id": dependent_task_id,
                "dependency_task_id": dependency_task_id,
            },
            description=(
                f"Add dependency: '{dependent_title}' "
                f"now requires '{dep_title}' to complete first"
            ),
        )

        desc = (
            f"Add dependency: '{dependent_title}' "
            f"now requires '{dep_title}' to complete first"
        )
        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "description": desc,
        }

    return add_dependency


def make_remove_dependency(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create a remove_dependency tool (requires confirmation)."""

    @tool
    async def remove_dependency(
        dependent_task_id: str, dependency_task_id: str
    ) -> dict[str, Any]:
        """Remove a dependency edge between two tasks. Requires confirmation.

        Args:
            dependent_task_id: The task that is currently blocked.
            dependency_task_id: The current prerequisite task.
        """
        # Get task titles for description
        dep_task = await db.get(Task, dependency_task_id)
        dependent_task = await db.get(Task, dependent_task_id)

        if dep_task is None or dep_task.board_id != board_id:
            return {
                "status": "failed",
                "error": "Dependency task not found on this board",
            }
        if dependent_task is None or dependent_task.board_id != board_id:
            return {
                "status": "failed",
                "error": "Dependent task not found on this board",
            }

        action = await create_pending_action(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            tool_name="remove_dependency",
            tool_args={
                "dependent_task_id": dependent_task_id,
                "dependency_task_id": dependency_task_id,
            },
            description=(
                f"Remove dependency: '{dependent_task.title}' "
                f"no longer requires '{dep_task.title}'"
            ),
        )

        desc = (
            f"Remove dependency: '{dependent_task.title}' "
            f"no longer requires '{dep_task.title}'"
        )
        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "description": desc,
        }

    return remove_dependency


def make_split_task(
    db: AsyncSession, board_id: str, user_id: str, thread_id: str
) -> Any:
    """Create a split_task tool (requires confirmation)."""

    @tool
    async def split_task(
        task_id: str, new_tasks: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Split one task into multiple smaller tasks.

        Requires confirmation. New tasks inherit the original's
        dependencies.

        Args:
            task_id: The UUID of the task to split.
            new_tasks: List of dicts with 'title' and optional 'description' keys.
        """
        task = await db.get(Task, task_id)
        if task is None or task.board_id != board_id:
            return {"status": "failed", "error": "Task not found on this board"}

        if task.is_goal_node:
            return {"status": "failed", "error": "Cannot split the goal node"}

        if len(new_tasks) < 2:
            return {"status": "failed", "error": "Must split into at least 2 tasks"}

        titles = [t.get("title", "Untitled") for t in new_tasks]

        action = await create_pending_action(
            db=db,
            user_id=user_id,
            thread_id=thread_id,
            tool_name="split_task",
            tool_args={"task_id": task_id, "new_tasks": new_tasks},
            description=f"Split task '{task.title}' into: {', '.join(titles)}",
        )

        return {
            "status": "pending_confirmation",
            "pending_action_id": action.id,
            "description": f"Split task '{task.title}' into: {', '.join(titles)}",
        }

    return split_task
