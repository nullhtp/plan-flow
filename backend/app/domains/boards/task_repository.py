"""Data-access layer for tasks and task dependencies."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Subtask, Task, TaskDependency


class TaskRepository:
    """Encapsulates all DB queries for :class:`Task` and :class:`TaskDependency`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Task CRUD ────────────────────────────────────────

    async def get_by_id(self, task_id: str) -> Task | None:
        """Fetch a task by primary key."""
        return await self.session.get(Task, task_id)

    async def create(self, task: Task) -> Task:
        """Persist a new task (flush only, caller commits)."""
        self.session.add(task)
        await self.session.flush()
        return task

    async def update(self, task: Task) -> None:
        """Mark a task as dirty so changes are flushed on next commit."""
        self.session.add(task)

    async def delete(self, task: Task) -> None:
        """Delete a task, its subtasks, and all dependency edges."""
        task_id = task.id
        # Delete subtasks
        await self.session.execute(delete(Subtask).where(Subtask.task_id == task_id))
        # Delete dependency edges (both directions)
        await self.session.execute(
            delete(TaskDependency).where(TaskDependency.dependent_task_id == task_id)
        )
        await self.session.execute(
            delete(TaskDependency).where(TaskDependency.dependency_task_id == task_id)
        )
        await self.session.delete(task)

    # ── Dependency queries ───────────────────────────────

    async def get_dependencies(self, task_id: str) -> list[Task]:
        """Return all prerequisite tasks for a given task."""
        stmt = (
            select(Task)
            .join(TaskDependency, TaskDependency.dependency_task_id == Task.id)
            .where(TaskDependency.dependent_task_id == task_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_dependents(self, task_id: str) -> list[Task]:
        """Return all tasks that depend on the given task."""
        stmt = (
            select(Task)
            .join(TaskDependency, TaskDependency.dependent_task_id == Task.id)
            .where(TaskDependency.dependency_task_id == task_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def are_dependencies_met(self, task_id: str) -> bool:
        """Check if all prerequisite tasks have status ``'done'``."""
        stmt = (
            select(func.count())
            .select_from(TaskDependency)
            .join(Task, TaskDependency.dependency_task_id == Task.id)
            .where(
                TaskDependency.dependent_task_id == task_id,
                Task.status != "done",
            )
        )
        result = await self.session.execute(stmt)
        unmet_count = result.scalar() or 0
        return unmet_count == 0

    async def create_dependency(
        self, dependent_task_id: str, dependency_task_id: str
    ) -> TaskDependency:
        """Create a dependency edge between two tasks."""
        dep = TaskDependency(
            dependent_task_id=dependent_task_id,
            dependency_task_id=dependency_task_id,
        )
        self.session.add(dep)
        return dep

    async def delete_dependencies_for_task(self, task_id: str) -> None:
        """Remove all dependency edges where *task_id* is either side."""
        await self.session.execute(
            delete(TaskDependency).where(TaskDependency.dependent_task_id == task_id)
        )
        await self.session.execute(
            delete(TaskDependency).where(TaskDependency.dependency_task_id == task_id)
        )


__all__ = ["TaskRepository"]
