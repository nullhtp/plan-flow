"""Data-access layer for the goals domain."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.goals.models import Goal, GoalStatus


class GoalRepository:
    """Encapsulates all database queries for :class:`Goal`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, goal_id: str) -> Goal | None:
        """Fetch a goal by primary key."""
        return await self.session.get(Goal, goal_id)

    async def get_for_user(self, goal_id: str, user_id: str) -> Goal | None:
        """Fetch a goal only if it belongs to *user_id*."""
        goal = await self.session.get(Goal, goal_id)
        if goal is None or goal.user_id != user_id:
            return None
        return goal

    async def create(self, goal: Goal) -> Goal:
        """Persist a new goal and return the refreshed instance."""
        self.session.add(goal)
        await self.session.commit()
        await self.session.refresh(goal)
        return goal

    async def update_status(self, goal: Goal, status: GoalStatus) -> None:
        """Update a goal's status and timestamp."""
        goal.status = status.value
        goal.updated_at = datetime.now(UTC)
        self.session.add(goal)
        await self.session.commit()
        await self.session.refresh(goal)

    async def update_ai_context(self, goal: Goal, ai_context: dict[str, Any]) -> None:
        """Replace the goal's ai_context and commit."""
        goal.ai_context = ai_context
        goal.updated_at = datetime.now(UTC)
        self.session.add(goal)
        await self.session.commit()
        await self.session.refresh(goal)

    async def delete(self, goal: Goal) -> None:
        """Remove a goal from the database."""
        await self.session.delete(goal)
        await self.session.commit()


__all__ = ["GoalRepository"]
