from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.domains.auth.models import User
from app.domains.auth.repository import UserRepository


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetch a user by email (case-insensitive)."""
    repo = UserRepository(session)
    return await repo.get_by_email(email)


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Fetch a user by primary key."""
    repo = UserRepository(session)
    return await repo.get_by_id(user_id)


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Create a new user with a hashed password.

    Raises ValueError if the email is already registered.
    """
    repo = UserRepository(session)
    existing = await repo.get_by_email(email)
    if existing is not None:
        raise ValueError("Email already registered")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
    )
    return await repo.create(user)


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """Verify credentials and return the user, or None on failure."""
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
