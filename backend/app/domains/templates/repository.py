"""Data-access layer for board templates."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.templates.models import (
    BoardTemplate,
    TemplateCategory,
    TemplateSubtask,
    TemplateTask,
    TemplateTaskDependency,
)


class TemplateCategoryRepository:
    """Encapsulates all database queries for :class:`TemplateCategory`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[TemplateCategory]:
        """Fetch all categories ordered by display_order."""
        stmt = select(TemplateCategory).order_by(TemplateCategory.display_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> TemplateCategory | None:
        """Fetch a category by primary key."""
        return await self.session.get(TemplateCategory, category_id)

    async def get_by_slug(self, slug: str) -> TemplateCategory | None:
        """Fetch a category by its slug."""
        stmt = select(TemplateCategory).where(TemplateCategory.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_public_by_category(self) -> dict[str, int]:
        """Return a mapping of category_id -> count of public templates."""
        stmt = (
            select(
                BoardTemplate.category_id,
                func.count().label("count"),
            )
            .where(
                BoardTemplate.visibility == "public",
                BoardTemplate.category_id.is_not(None),
            )
            .group_by(BoardTemplate.category_id)
        )
        result = await self.session.execute(stmt)
        return {row.category_id: row.count for row in result.all()}


class BoardTemplateRepository:
    """Encapsulates all database queries for :class:`BoardTemplate`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, template: BoardTemplate) -> BoardTemplate:
        """Persist a new template (flush only, caller commits)."""
        self.session.add(template)
        await self.session.flush()
        return template

    async def get_by_id(self, template_id: str) -> BoardTemplate | None:
        """Fetch a template by primary key (no relations loaded)."""
        return await self.session.get(BoardTemplate, template_id)

    async def get_with_relations(self, template_id: str) -> BoardTemplate | None:
        """Fetch a template with tasks, subtasks, and dependencies."""
        stmt = (
            select(BoardTemplate)
            .options(
                selectinload(BoardTemplate.tasks).selectinload(TemplateTask.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(BoardTemplate.dependencies),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                selectinload(BoardTemplate.category),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
            .where(BoardTemplate.id == template_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        *,
        visibility: str = "public",
        user_id: str | None = None,
        category_slug: str | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        """List templates with filtering, search, and pagination.

        Returns dict with keys: items, total, page, per_page, total_pages.
        """
        stmt = select(BoardTemplate).options(
            selectinload(BoardTemplate.category),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )

        # Visibility filter
        if visibility == "mine" and user_id:
            stmt = stmt.where(BoardTemplate.user_id == user_id)
        else:
            stmt = stmt.where(BoardTemplate.visibility == "public")

        # Category filter
        if category_slug:
            stmt = stmt.join(TemplateCategory).where(
                TemplateCategory.slug == category_slug
            )

        # Search filter
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    BoardTemplate.title.ilike(pattern),
                    BoardTemplate.description.ilike(pattern),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginate
        stmt = (
            stmt.order_by(BoardTemplate.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page) if per_page > 0 else 0,
        }

    async def update(self, template: BoardTemplate) -> None:
        """Mark a template as dirty so changes are flushed on next commit."""
        self.session.add(template)

    async def delete(self, template: BoardTemplate) -> None:
        """Delete a template (cascade deletes tasks, deps, subtasks)."""
        await self.session.delete(template)


class TemplateTaskRepository:
    """Encapsulates database queries for :class:`TemplateTask`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, tasks: list[TemplateTask]) -> list[TemplateTask]:
        """Persist multiple template tasks (flush only)."""
        self.session.add_all(tasks)
        await self.session.flush()
        return tasks

    async def list_by_template(self, template_id: str) -> list[TemplateTask]:
        """Fetch all tasks for a template with subtasks."""
        stmt = (
            select(TemplateTask)
            .options(selectinload(TemplateTask.subtasks))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            .where(TemplateTask.template_id == template_id)
            .order_by(TemplateTask.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TemplateTaskDependencyRepository:
    """Encapsulates database queries for :class:`TemplateTaskDependency`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(
        self, deps: list[TemplateTaskDependency]
    ) -> list[TemplateTaskDependency]:
        """Persist multiple template task dependencies (flush only)."""
        self.session.add_all(deps)
        await self.session.flush()
        return deps


class TemplateSubtaskRepository:
    """Encapsulates database queries for :class:`TemplateSubtask`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(
        self, subtasks: list[TemplateSubtask]
    ) -> list[TemplateSubtask]:
        """Persist multiple template subtasks (flush only)."""
        self.session.add_all(subtasks)
        await self.session.flush()
        return subtasks
