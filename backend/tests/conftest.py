from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app.core.config import settings
from app.core.db import get_session
from app.core.security import create_access_token, hash_password
from app.core.types import BoardSkeletonOutput, BoardSkeletonTaskOutput
from app.domains.auth.models import User
from app.domains.boards.models import Board, BoardMember, BoardShare, Subtask, Task, TaskDependency  # noqa: F401
from app.domains.boards.task_service import create_board_from_skeleton
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
    """Create tables before each test, drop them after.

    Uses DROP SCHEMA CASCADE in teardown to handle circular FK
    dependencies (board <-> task).
    """
    async with _engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        await conn.exec_driver_sql("CREATE SCHEMA public")
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")


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
                "language": "en",
                "rejection_reason": None,
                "refinement_suggestions": [],
            },
            "rounds": [
                {
                    "round": 1,
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
                            "options": [
                                "Visa requirements",
                                "Housing costs",
                                "Language barrier",
                            ],
                            "rationale": "Helps identify potential blockers",
                            "required": False,
                        },
                    ],
                    "answers": {},
                    "readiness": {
                        "score": 0.0,
                        "covered_dimensions": [],
                        "uncovered_dimensions": ["timeline", "budget", "housing"],
                        "summary": "No answers collected yet.",
                    },
                }
            ],
        },
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


@pytest.fixture
async def answered_goal(session: AsyncSession, test_user: User) -> Goal:
    """Create a test goal in 'answered' status with full AI context."""
    goal = Goal(
        user_id=test_user.id,
        title="Relocate to Lisbon",
        original_input="Move from Berlin to Lisbon within 3 months",
        status=GoalStatus.ANSWERED,
        ai_context={
            "classification": {
                "domain": "relocation",
                "complexity": 4,
                "confidence": 0.9,
                "dimensions": ["timeline", "budget", "housing", "logistics"],
                "suggested_title": "Relocate to Lisbon",
                "language": "en",
                "rejection_reason": None,
                "refinement_suggestions": [],
            },
            "rounds": [
                {
                    "round": 1,
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
                            "options": [
                                "Visa requirements",
                                "Housing costs",
                                "Language barrier",
                            ],
                            "rationale": "Helps identify potential blockers",
                            "required": False,
                        },
                    ],
                    "answers": {
                        "q1": "5000-10000",
                        "q2": "Remote work",
                        "q3": "Need to bring my cat",
                    },
                    "readiness": {
                        "score": 0.8,
                        "covered_dimensions": [
                            "timeline",
                            "budget",
                            "housing",
                            "logistics",
                        ],
                        "uncovered_dimensions": [],
                        "summary": "Sufficient information collected.",
                    },
                }
            ],
        },
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


def make_skeleton(
    board_title: str = "Test Board",
    tasks: list[dict] | None = None,
) -> BoardSkeletonOutput:
    """Helper to create a BoardSkeletonOutput for testing."""
    if tasks is None:
        tasks = [
            {"id": "t1", "title": "Task 1", "depends_on": [], "is_goal_node": False},
            {"id": "t2", "title": "Task 2", "depends_on": [], "is_goal_node": False},
            {
                "id": "t3",
                "title": "Goal Task",
                "depends_on": ["t1", "t2"],
                "is_goal_node": True,
            },
        ]
    return BoardSkeletonOutput(
        board_title=board_title,
        tasks=[BoardSkeletonTaskOutput(**t) for t in tasks],
    )


async def create_test_board(
    session: AsyncSession,
    goal: Goal,
    skeleton: BoardSkeletonOutput | None = None,
) -> tuple[Board, dict[str, str]]:
    """Create a board directly in the DB from a skeleton (bypasses API/AI).

    Returns (board, ai_id_to_db_id_mapping).
    Also transitions the goal to 'active' status.
    """
    if skeleton is None:
        skeleton = make_skeleton()

    board, ai_id_to_db_id = await create_board_from_skeleton(session, goal.id, skeleton)

    # Transition goal to active
    goal.status = GoalStatus.ACTIVE.value
    session.add(goal)
    await session.commit()

    # Re-fetch the board with all relationships eager-loaded so that
    # tools can access task.subtasks, task.dependencies, task.dependents,
    # and dependency_task/dependent_task without triggering lazy loads
    # (which fail under async sessions).
    stmt = (
        sa_select(Board)
        .options(
            selectinload(Board.tasks).selectinload(Task.subtasks),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            selectinload(Board.tasks)
            .selectinload(Task.dependencies)
            .selectinload(TaskDependency.dependency_task),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            selectinload(Board.tasks)
            .selectinload(Task.dependents)
            .selectinload(TaskDependency.dependent_task),  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )
        .where(Board.id == board.id)  # pyright: ignore[reportArgumentType]
    )
    result = await session.execute(stmt)
    loaded_board = result.scalar_one()

    return loaded_board, ai_id_to_db_id
