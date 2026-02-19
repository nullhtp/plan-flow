"""PendingAction CRUD service and tool execution dispatcher.

Handles confirm/reject lifecycle and dispatches confirmed actions to the
appropriate board/task mutations.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import PendingAction
from app.domains.boards.models import Board, Subtask, Task, TaskDependency
from app.domains.boards.subtask_service import sync_task_status_from_subtasks
from app.domains.boards.task_service import are_dependencies_met

logger = logging.getLogger(__name__)


# ── CRUD ─────────────────────────────────────────────────


async def get_pending_action(
    db: AsyncSession, action_id: str, user_id: str
) -> PendingAction | None:
    """Fetch a pending action owned by user_id, or None."""
    action = await db.get(PendingAction, action_id)
    if action is None or action.user_id != user_id:
        return None
    return action


async def confirm_action(
    db: AsyncSession, action_id: str, user_id: str
) -> dict[str, Any]:
    """Confirm and execute a pending action.

    Returns a result dict with 'status' key:
    - 'executed': action was carried out successfully
    - 'failed': execution error (details in 'error')
    - 'not_found': action doesn't exist or wrong user
    - 'expired': action has expired
    - 'already_resolved': action was already confirmed/rejected
    """
    action = await get_pending_action(db, action_id, user_id)
    if action is None:
        return {"status": "not_found", "error": "Action not found"}

    if action.status != "pending":
        return {
            "status": "already_resolved",
            "error": f"Action already {action.status}",
        }

    if action.expires_at < datetime.now(UTC):
        action.status = "expired"
        db.add(action)
        await db.commit()
        return {"status": "expired", "error": "Action has expired"}

    # Execute the tool
    try:
        result = await _dispatch_tool(db, action.tool_name, action.tool_args, user_id)
        action.status = "confirmed"
        action.result = result
        db.add(action)
        await db.commit()
        return {"status": "executed", "result": result}
    except Exception as e:
        await db.rollback()
        logger.exception("Tool execution failed for action %s", action_id)
        action.status = "confirmed"
        action.result = {"error": str(e)}
        db.add(action)
        await db.commit()
        return {"status": "failed", "error": str(e)}


async def reject_action(
    db: AsyncSession, action_id: str, user_id: str
) -> dict[str, Any]:
    """Reject a pending action.

    Returns a result dict with 'status' key.
    """
    action = await get_pending_action(db, action_id, user_id)
    if action is None:
        return {"status": "not_found", "error": "Action not found"}

    if action.status != "pending":
        return {
            "status": "already_resolved",
            "error": f"Action already {action.status}",
        }

    action.status = "rejected"
    db.add(action)
    await db.commit()
    return {"status": "rejected", "description": action.description}


# ── Tool Execution Dispatcher ────────────────────────────


async def _dispatch_tool(
    db: AsyncSession,
    tool_name: str,
    tool_args: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    """Execute the actual mutation for a confirmed tool action.

    Each tool_name maps to a handler that performs the real DB operation.
    """
    handlers: dict[str, Any] = {
        "update_task_status": _execute_update_task_status,
        "delete_subtask": _execute_delete_subtask,
        "add_task": _execute_add_task,
        "remove_task": _execute_remove_task,
        "add_dependency": _execute_add_dependency,
        "remove_dependency": _execute_remove_dependency,
        "split_task": _execute_split_task,
    }

    handler = handlers.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}"}

    return await handler(db, tool_args, user_id)


async def _execute_update_task_status(
    db: AsyncSession, args: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Execute a confirmed status change."""
    task_id = args["task_id"]
    new_status = args["new_status"]

    task = await db.get(Task, task_id)
    if task is None:
        return {"error": "Task not found"}

    # Re-validate the transition at execution time
    if task.status == "not_started" and new_status == "in_progress":
        deps_met = await are_dependencies_met(db, task.id)
        if not deps_met:
            return {"error": "Cannot start task: not all dependencies are completed"}
    elif task.status == "not_started" and new_status == "done":
        return {"error": "Cannot complete task directly: must be in progress first"}

    old_status = task.status
    task.status = new_status
    task.updated_at = datetime.now(UTC)
    db.add(task)
    await db.commit()

    return {
        "task_id": task.id,
        "title": task.title,
        "old_status": old_status,
        "new_status": new_status,
    }


async def _execute_delete_subtask(
    db: AsyncSession, args: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Execute a confirmed subtask deletion."""
    subtask_id = args["subtask_id"]
    subtask = await db.get(Subtask, subtask_id)
    if subtask is None:
        return {"error": "Subtask not found"}

    title = subtask.title
    task_id = subtask.task_id
    task = await db.get(Task, task_id)
    await db.delete(subtask)

    # Re-sync parent task status after subtask removal
    if task is not None:
        await sync_task_status_from_subtasks(db, task)

    await db.commit()

    return {"subtask_id": subtask_id, "title": title, "task_id": task_id}


async def _execute_add_task(
    db: AsyncSession, args: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Execute a confirmed task addition."""
    board_id = args["board_id"]
    title = args["title"]
    description = args.get("description", "")
    depends_on_ids: list[str] = args.get("depends_on_ids", [])
    dependent_ids: list[str] = args.get("dependent_ids", [])

    board = await db.get(Board, board_id)
    if board is None:
        return {"error": "Board not found"}

    # Create the task
    task = Task(
        board_id=board_id,
        title=title,
        description=description,
        status="not_started",
    )
    db.add(task)
    await db.flush()

    # Create dependency edges
    for dep_id in depends_on_ids:
        edge = TaskDependency(
            dependency_task_id=dep_id,
            dependent_task_id=task.id,
        )
        db.add(edge)

    for dependent_id in dependent_ids:
        edge = TaskDependency(
            dependency_task_id=task.id,
            dependent_task_id=dependent_id,
        )
        db.add(edge)

    await db.commit()

    return {
        "task_id": task.id,
        "title": title,
        "board_id": board_id,
    }


async def _execute_remove_task(
    db: AsyncSession, args: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Execute a confirmed task removal."""
    task_id = args["task_id"]
    task = await db.get(Task, task_id)
    if task is None:
        return {"error": "Task not found"}

    if task.is_goal_node:
        return {"error": "Cannot remove the goal node"}

    title = task.title
    board_id = task.board_id

    # Delete subtasks
    await db.execute(
        delete(Subtask).where(Subtask.task_id == task_id)  # pyright: ignore[reportArgumentType]
    )
    # Delete dependency edges
    await db.execute(
        delete(TaskDependency).where(TaskDependency.dependent_task_id == task_id)
    )
    await db.execute(
        delete(TaskDependency).where(TaskDependency.dependency_task_id == task_id)
    )
    await db.delete(task)
    await db.commit()

    return {"task_id": task_id, "title": title, "board_id": board_id}


async def _execute_add_dependency(
    db: AsyncSession, args: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Execute a confirmed dependency addition."""
    dependent_task_id = args["dependent_task_id"]
    dependency_task_id = args["dependency_task_id"]

    # Verify both tasks exist
    dependent = await db.get(Task, dependent_task_id)
    dependency = await db.get(Task, dependency_task_id)
    if dependent is None or dependency is None:
        return {"error": "One or both tasks not found"}

    edge = TaskDependency(
        dependency_task_id=dependency_task_id,
        dependent_task_id=dependent_task_id,
    )
    db.add(edge)
    await db.commit()

    return {
        "dependent_task_id": dependent_task_id,
        "dependency_task_id": dependency_task_id,
        "dependent_title": dependent.title,
        "dependency_title": dependency.title,
    }


async def _execute_remove_dependency(
    db: AsyncSession, args: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Execute a confirmed dependency removal."""
    dependent_task_id = args["dependent_task_id"]
    dependency_task_id = args["dependency_task_id"]

    result = await db.execute(
        delete(TaskDependency).where(
            TaskDependency.dependent_task_id == dependent_task_id,
            TaskDependency.dependency_task_id == dependency_task_id,
        )
    )

    if result.rowcount == 0:  # pyright: ignore[reportUnknownMemberType]
        return {"error": "Dependency edge not found"}

    await db.commit()

    return {
        "dependent_task_id": dependent_task_id,
        "dependency_task_id": dependency_task_id,
    }


async def _execute_split_task(
    db: AsyncSession, args: dict[str, Any], user_id: str
) -> dict[str, Any]:
    """Execute a confirmed task split.

    Replaces the original task with N new tasks that inherit its dependencies
    and dependents. The new tasks form a chain within themselves (each depends
    on the previous one) to maintain ordering.
    """
    task_id = args["task_id"]
    new_tasks_data: list[dict[str, str]] = args["new_tasks"]

    task = await db.get(Task, task_id)
    if task is None:
        return {"error": "Task not found"}

    if task.is_goal_node:
        return {"error": "Cannot split the goal node"}

    board_id = task.board_id

    # Collect existing dependency info
    stmt_deps = select(TaskDependency).where(
        TaskDependency.dependent_task_id == task_id
    )
    result_deps = await db.execute(stmt_deps)
    incoming_edges = result_deps.scalars().all()
    incoming_dep_ids = [e.dependency_task_id for e in incoming_edges]

    stmt_dependents = select(TaskDependency).where(
        TaskDependency.dependency_task_id == task_id
    )
    result_dependents = await db.execute(stmt_dependents)
    outgoing_edges = result_dependents.scalars().all()
    outgoing_dep_ids = [e.dependent_task_id for e in outgoing_edges]

    # Delete the original task and its edges
    await db.execute(
        delete(Subtask).where(Subtask.task_id == task_id)  # pyright: ignore[reportArgumentType]
    )
    await db.execute(
        delete(TaskDependency).where(TaskDependency.dependent_task_id == task_id)
    )
    await db.execute(
        delete(TaskDependency).where(TaskDependency.dependency_task_id == task_id)
    )
    await db.delete(task)
    await db.flush()

    # Create new tasks
    new_task_ids: list[str] = []
    for td in new_tasks_data:
        new_task = Task(
            board_id=board_id,
            title=td.get("title", "Untitled"),
            description=td.get("description", ""),
            status="not_started",
        )
        db.add(new_task)
        await db.flush()
        new_task_ids.append(new_task.id)

    # First new task inherits all incoming dependencies
    for dep_id in incoming_dep_ids:
        db.add(
            TaskDependency(
                dependency_task_id=dep_id,
                dependent_task_id=new_task_ids[0],
            )
        )

    # Last new task gets all outgoing dependents
    for dep_id in outgoing_dep_ids:
        db.add(
            TaskDependency(
                dependency_task_id=new_task_ids[-1],
                dependent_task_id=dep_id,
            )
        )

    # Chain new tasks: each depends on previous
    for i in range(1, len(new_task_ids)):
        db.add(
            TaskDependency(
                dependency_task_id=new_task_ids[i - 1],
                dependent_task_id=new_task_ids[i],
            )
        )

    await db.commit()

    return {
        "original_task_id": task_id,
        "original_title": task.title,
        "new_task_ids": new_task_ids,
        "board_id": board_id,
    }
