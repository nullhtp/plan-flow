from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.db import get_session
from app.core.security import create_access_token, hash_password
from app.domains.auth.models import User
from app.domains.goals.models import Goal, GoalStatus
from app.main import app

# Use NullPool to avoid connection-sharing issues across async event loops.
# Use the dedicated test database to avoid destroying dev/prod data.
_engine = create_async_engine(
    settings.test_database_url, echo=False, poolclass=NullPool
)
_session_factory = async_sessionmaker(
    _engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create tables before each test, drop them after."""
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with _session_factory() as session:
        yield session


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with the test DB session."""

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)  # pyright: ignore[reportArgumentType]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(session: AsyncSession) -> User:
    """Create and return a test user."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def auth_client(
    client: AsyncClient, test_user: User
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated HTTP test client with access token cookie."""
    token = create_access_token(test_user.id)
    client.cookies.set("access_token", token)
    yield client


@pytest.fixture
async def test_goal(session: AsyncSession, test_user: User) -> Goal:
    """Create a test goal in 'questioning' status with sample AI context."""
    goal = Goal(
        user_id=test_user.id,
        title="Relocate to Lisbon",
        original_input="Move from Berlin to Lisbon within 3 months",
        status=GoalStatus.QUESTIONING,
        ai_context={
            "classification": {
                "domain": "relocation",
                "complexity": 4,
                "confidence": 0.9,
                "dimensions": ["timeline", "budget", "housing"],
                "suggested_title": "Relocate to Lisbon",
                "rejection_reason": None,
                "refinement_suggestions": [],
            },
            "questions": [
                {
                    "id": "q1",
                    "text": "What is your budget?",
                    "type": "select",
                    "options": ["< 5000", "5000-10000", "> 10000"],
                    "rationale": "Budget determines housing options",
                    "required": True,
                },
                {
                    "id": "q2",
                    "text": "Do you have a job lined up?",
                    "type": "select",
                    "options": ["Yes", "No", "Remote work"],
                    "rationale": "Employment affects visa and timeline",
                    "required": True,
                },
                {
                    "id": "q3",
                    "text": "Any specific concerns?",
                    "type": "text",
                    "options": None,
                    "rationale": "Helps identify potential blockers",
                    "required": False,
                },
            ],
        },
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal
