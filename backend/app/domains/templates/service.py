"""Business logic for board templates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.board_repository import BoardRepository
from app.domains.boards.models import Board, Subtask, Task, TaskDependency
from app.domains.goals.models import Goal, GoalStatus
from app.domains.templates.models import (
    BoardTemplate,
    TemplateSubtask,
    TemplateTask,
    TemplateTaskDependency,
)
from app.domains.templates.repository import (
    BoardTemplateRepository,
    TemplateCategoryRepository,
    TemplateSubtaskRepository,
    TemplateTaskDependencyRepository,
    TemplateTaskRepository,
)


async def list_categories(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Return all categories with public template counts."""
    cat_repo = TemplateCategoryRepository(session)
    categories = await cat_repo.list_all()
    counts = await cat_repo.count_public_by_category()

    return [
        {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "icon": cat.icon,
            "template_count": counts.get(cat.id, 0),
        }
        for cat in categories
    ]


async def create_template_from_board(
    session: AsyncSession,
    user_id: str,
    board_id: str,
    title: str,
    description: str | None = None,
    category_id: str | None = None,
    visibility: str = "private",
) -> BoardTemplate:
    """Snapshot a board into a new template.

    Validates ownership and copies tasks, dependencies, and subtasks
    in a single transaction.
    """
    # Validate board ownership
    board_repo = BoardRepository(session)
    board = await board_repo.get_with_relations(board_id)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )

    # Trace ownership to user
    goal = await session.get(Goal, board.goal_id) if board.goal_id else None
    if goal is None or goal.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Board not found"
        )

    # Validate board has tasks
    if not board.tasks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot create template from a board with no tasks",
        )

    # Validate category exists if provided
    if category_id:
        cat_repo = TemplateCategoryRepository(session)
        cat = await cat_repo.get_by_id(category_id)
        if cat is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid category",
            )

    # Create the template
    template_repo = BoardTemplateRepository(session)
    template = BoardTemplate(
        user_id=user_id,
        category_id=category_id,
        title=title,
        description=description,
        visibility=visibility,
        source_board_id=board_id,
        task_count=len(board.tasks),
    )
    await template_repo.create(template)

    # Map original task IDs to new template task IDs
    task_id_map: dict[str, str] = {}
    task_repo = TemplateTaskRepository(session)
    template_tasks: list[TemplateTask] = []

    for task in board.tasks:
        tt = TemplateTask(
            template_id=template.id,
            title=task.title,
            description=task.description,
            is_goal_node=task.is_goal_node,
            priority=task.priority,
            estimated_minutes=task.estimated_minutes,
        )
        template_tasks.append(tt)
        task_id_map[task.id] = tt.id

    await task_repo.bulk_create(template_tasks)

    # Copy dependencies
    dep_repo = TemplateTaskDependencyRepository(session)
    template_deps: list[TemplateTaskDependency] = []
    for task in board.tasks:
        for dep in task.dependencies:
            # Only add if both tasks are in our map (same board)
            if dep.dependency_task_id in task_id_map and dep.dependent_task_id in task_id_map:
                td = TemplateTaskDependency(
                    template_id=template.id,
                    dependent_task_id=task_id_map[dep.dependent_task_id],
                    dependency_task_id=task_id_map[dep.dependency_task_id],
                )
                template_deps.append(td)

    # Deduplicate (edges can appear from both sides)
    seen: set[tuple[str, str]] = set()
    unique_deps: list[TemplateTaskDependency] = []
    for td in template_deps:
        key = (td.dependent_task_id, td.dependency_task_id)
        if key not in seen:
            seen.add(key)
            unique_deps.append(td)

    if unique_deps:
        await dep_repo.bulk_create(unique_deps)

    # Copy subtasks
    subtask_repo = TemplateSubtaskRepository(session)
    template_subtasks: list[TemplateSubtask] = []
    for task in board.tasks:
        new_task_id = task_id_map[task.id]
        for subtask in task.subtasks:
            ts = TemplateSubtask(
                template_task_id=new_task_id,
                title=subtask.title,
                position=subtask.position,
            )
            template_subtasks.append(ts)

    if template_subtasks:
        await subtask_repo.bulk_create(template_subtasks)

    await session.commit()
    return template


async def get_template(
    session: AsyncSession,
    template_id: str,
    user_id: str,
) -> BoardTemplate:
    """Retrieve a template with full relations, respecting visibility."""
    repo = BoardTemplateRepository(session)
    template = await repo.get_with_relations(template_id)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    # Private templates only visible to creator
    if template.visibility == "private" and template.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    return template


async def list_templates(
    session: AsyncSession,
    user_id: str,
    *,
    visibility: str = "public",
    category_slug: str | None = None,
    search: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """List templates with filtering, search, and pagination."""
    repo = BoardTemplateRepository(session)
    return await repo.list_templates(
        visibility=visibility,
        user_id=user_id,
        category_slug=category_slug,
        search=search,
        page=page,
        per_page=per_page,
    )


async def update_template(
    session: AsyncSession,
    template_id: str,
    user_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    category_id: str | None = None,
    visibility: str | None = None,
) -> BoardTemplate:
    """Update template metadata. Only the creator can update."""
    repo = BoardTemplateRepository(session)
    template = await repo.get_by_id(template_id)

    if template is None or template.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    if title is not None:
        template.title = title
    if description is not None:
        template.description = description
    if category_id is not None:
        cat_repo = TemplateCategoryRepository(session)
        cat = await cat_repo.get_by_id(category_id)
        if cat is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid category",
            )
        template.category_id = category_id
    if visibility is not None:
        template.visibility = visibility

    template.updated_at = datetime.now(UTC)
    await repo.update(template)
    await session.commit()

    return template


async def delete_template(
    session: AsyncSession,
    template_id: str,
    user_id: str,
) -> None:
    """Delete a template. Only the creator can delete."""
    repo = BoardTemplateRepository(session)
    template = await repo.get_by_id(template_id)

    if template is None or template.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    await repo.delete(template)
    await session.commit()


async def create_board_from_template(
    session: AsyncSession,
    template_id: str,
    user_id: str,
    title: str | None = None,
) -> dict[str, str]:
    """Create a new goal + board from a template.

    Returns dict with board_id, goal_id, and title.
    """
    repo = BoardTemplateRepository(session)
    template = await repo.get_with_relations(template_id)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    # Validate access: public or owned by user
    if template.visibility == "private" and template.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    board_title = title or template.title

    # Create goal
    goal = Goal(
        user_id=user_id,
        title=board_title,
        original_input=f"Created from template: {template.title}",
        status=GoalStatus.ACTIVE.value,
        ai_context={"source": "template", "template_id": template.id},
    )
    session.add(goal)
    await session.flush()

    # Create board
    board = Board(
        goal_id=goal.id,
        title=board_title,
    )
    session.add(board)
    await session.flush()

    # Map template task IDs to new task IDs
    task_id_map: dict[str, str] = {}
    new_tasks: list[Task] = []

    for tt in template.tasks:
        task = Task(
            board_id=board.id,
            title=tt.title,
            description=tt.description,
            status="not_started",
            is_goal_node=tt.is_goal_node,
            priority=tt.priority,
            estimated_minutes=tt.estimated_minutes,
        )
        new_tasks.append(task)
        task_id_map[tt.id] = task.id

    session.add_all(new_tasks)
    await session.flush()

    # Copy dependencies
    new_deps: list[TaskDependency] = []
    for td in template.dependencies:
        dep_task_id = task_id_map.get(td.dependent_task_id)
        prereq_task_id = task_id_map.get(td.dependency_task_id)
        if dep_task_id and prereq_task_id:
            new_deps.append(
                TaskDependency(
                    dependent_task_id=dep_task_id,
                    dependency_task_id=prereq_task_id,
                )
            )

    if new_deps:
        session.add_all(new_deps)
        await session.flush()

    # Copy subtasks
    new_subtasks: list[Subtask] = []
    for tt in template.tasks:
        new_task_id = task_id_map[tt.id]
        for ts in tt.subtasks:
            new_subtasks.append(
                Subtask(
                    task_id=new_task_id,
                    title=ts.title,
                    completed=False,
                    position=ts.position,
                )
            )

    if new_subtasks:
        session.add_all(new_subtasks)
        await session.flush()

    await session.commit()

    return {
        "board_id": board.id,
        "goal_id": goal.id,
        "title": board_title,
    }
