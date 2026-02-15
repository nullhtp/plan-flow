from __future__ import annotations

from typing import cast

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.domains.auth.models import User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetch a user by email (case-insensitive)."""
    condition = cast(ColumnElement[bool], User.email == email.lower())
    stmt = select(User).where(condition)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Fetch a user by primary key."""
    return await session.get(User, user_id)


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Create a new user with a hashed password.

    Raises ValueError if the email is already registered.
    """
    existing = await get_user_by_email(session, email)
    if existing is not None:
        raise ValueError("Email already registered")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """Verify credentials and return the user, or None on failure."""
    user = await get_user_by_email(session, email)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
