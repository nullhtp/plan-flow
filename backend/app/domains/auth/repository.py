"""Data-access layer for the auth domain."""

from __future__ import annotations

from typing import cast

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.models import User


class UserRepository:
    """Encapsulates all database queries for :class:`User`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch a user by primary key."""
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email (case-insensitive)."""
        condition = cast(ColumnElement[bool], User.email == email.lower())
        stmt = select(User).where(condition)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a new user and return the refreshed instance."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user


__all__ = ["UserRepository"]
