"""Integration tests for the templates API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.auth.models import User
from app.domains.boards.models import Board
from app.domains.goals.models import Goal, GoalStatus
from app.domains.templates.models import (
    TemplateCategory,
)
from tests.conftest import create_test_board

# ── Helpers ──────────────────────────────────────────────


async def _seed_categories(session: AsyncSession) -> list[TemplateCategory]:
    """Seed test categories."""
    categories = [
        TemplateCategory(name="Travel", slug="travel", display_order=1),
        TemplateCategory(name="Career", slug="career", display_order=2),
    ]
    session.add_all(categories)
    await session.commit()
    for c in categories:
        await session.refresh(c)
    return categories


async def _create_board_with_tasks(
    session: AsyncSession, goal: Goal
) -> tuple[Board, dict[str, str]]:
    """Create a test board with tasks and dependencies."""
    return await create_test_board(session, goal)


async def _create_template(
    auth_client: AsyncClient,
    board_id: str,
    title: str = "My Template",
    visibility: str = "private",
    category_id: str | None = None,
) -> dict:
    """Helper to create a template via API."""
    body: dict = {
        "board_id": board_id,
        "title": title,
        "visibility": visibility,
    }
    if category_id:
        body["category_id"] = category_id
    resp = await auth_client.post("/api/templates", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Categories Endpoint ──────────────────────────────────


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, session: AsyncSession) -> None:
    """GET /api/templates/categories returns seeded categories."""
    await _seed_categories(session)
    resp = await client.get("/api/templates/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["slug"] == "travel"
    assert data[0]["template_count"] == 0


# ── Create Template ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_template_from_board(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """POST /api/templates creates a template from a board."""
    board, _id_map = await _create_board_with_tasks(session, answered_goal)

    data = await _create_template(auth_client, board.id)

    assert data["title"] == "My Template"
    assert data["visibility"] == "private"
    assert data["task_count"] == 3
    assert len(data["tasks"]) == 3
    assert len(data["edges"]) == 2  # t3 depends on t1 and t2


@pytest.mark.asyncio
async def test_create_template_from_other_user_board_rejected(
    auth_client: AsyncClient,
    session: AsyncSession,
) -> None:
    """POST /api/templates with another user's board returns 404."""
    # Create another user and their board
    other_user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)

    other_goal = Goal(
        user_id=other_user.id,
        title="Other Goal",
        original_input="Other goal",
        status=GoalStatus.ANSWERED,
        ai_context={},
    )
    session.add(other_goal)
    await session.commit()
    await session.refresh(other_goal)

    board, _ = await create_test_board(session, other_goal)

    resp = await auth_client.post(
        "/api/templates",
        json={"board_id": board.id, "title": "Stolen Template"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_template_empty_board_rejected(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """POST /api/templates for a board with no tasks returns 422."""
    # Create an empty board directly
    board = Board(goal_id=answered_goal.id, title="Empty Board")
    session.add(board)
    answered_goal.status = GoalStatus.ACTIVE.value
    session.add(answered_goal)
    await session.commit()
    await session.refresh(board)

    resp = await auth_client.post(
        "/api/templates",
        json={"board_id": board.id, "title": "Empty Template"},
    )
    assert resp.status_code == 422


# ── List Templates ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_public_templates(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """GET /api/templates?visibility=public returns public templates."""
    board, _ = await _create_board_with_tasks(session, answered_goal)

    # Create public template
    await _create_template(auth_client, board.id, "Public Template", "public")
    # Create private template
    await _create_template(auth_client, board.id, "Private Template", "private")

    resp = await auth_client.get("/api/templates?visibility=public")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Public Template"


@pytest.mark.asyncio
async def test_list_own_templates(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """GET /api/templates?visibility=mine returns all own templates."""
    board, _ = await _create_board_with_tasks(session, answered_goal)

    await _create_template(auth_client, board.id, "Public Template", "public")
    await _create_template(auth_client, board.id, "Private Template", "private")

    resp = await auth_client.get("/api/templates?visibility=mine")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_list_templates_with_category_filter(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """GET /api/templates?category=travel filters by category."""
    categories = await _seed_categories(session)
    board, _ = await _create_board_with_tasks(session, answered_goal)

    await _create_template(
        auth_client, board.id, "Travel Template", "public", categories[0].id
    )
    await _create_template(
        auth_client, board.id, "Career Template", "public", categories[1].id
    )

    resp = await auth_client.get("/api/templates?category=travel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Travel Template"


@pytest.mark.asyncio
async def test_list_templates_search(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """GET /api/templates?search=relocation filters by keyword."""
    board, _ = await _create_board_with_tasks(session, answered_goal)

    await _create_template(auth_client, board.id, "Relocation Plan", "public")
    await _create_template(auth_client, board.id, "Wedding Plan", "public")

    resp = await auth_client.get("/api/templates?search=relocation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Relocation Plan"


@pytest.mark.asyncio
async def test_list_templates_pagination(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """GET /api/templates supports pagination."""
    board, _ = await _create_board_with_tasks(session, answered_goal)

    for i in range(5):
        await _create_template(auth_client, board.id, f"Template {i}", "public")

    resp = await auth_client.get("/api/templates?page=1&per_page=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["total_pages"] == 3


# ── Get Template Detail ──────────────────────────────────


@pytest.mark.asyncio
async def test_get_template_detail(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """GET /api/templates/:id returns full template with tasks and edges."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "Detail Test", "public")

    resp = await auth_client.get(f"/api/templates/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Detail Test"
    assert len(data["tasks"]) == 3
    assert len(data["edges"]) == 2


@pytest.mark.asyncio
async def test_get_private_template_by_other_user_rejected(
    auth_client: AsyncClient,
    client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """GET /api/templates/:id for another user's private template returns 404."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "Private", "private")

    # Create another user and authenticate
    other_user = User(
        email="other2@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)
    other_token = create_access_token(other_user.id)
    client.cookies.set("access_token", other_token)

    resp = await client.get(f"/api/templates/{created['id']}")
    assert resp.status_code == 404


# ── Update Template ──────────────────────────────────────


@pytest.mark.asyncio
async def test_update_template(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """PATCH /api/templates/:id updates template metadata."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "Original", "private")

    resp = await auth_client.patch(
        f"/api/templates/{created['id']}",
        json={"title": "Updated", "visibility": "public"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated"
    assert data["visibility"] == "public"


@pytest.mark.asyncio
async def test_update_template_by_non_creator_rejected(
    auth_client: AsyncClient,
    client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """PATCH /api/templates/:id by non-creator returns 404."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "Original", "public")

    other_user = User(
        email="other3@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)
    client.cookies.set("access_token", create_access_token(other_user.id))

    resp = await client.patch(
        f"/api/templates/{created['id']}",
        json={"title": "Hijacked"},
    )
    assert resp.status_code == 404


# ── Delete Template ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_template(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """DELETE /api/templates/:id deletes the template."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "To Delete")

    resp = await auth_client.delete(f"/api/templates/{created['id']}")
    assert resp.status_code == 204

    # Confirm deleted
    resp = await auth_client.get(f"/api/templates/{created['id']}")
    assert resp.status_code == 404


# ── Create Board from Template ───────────────────────────


@pytest.mark.asyncio
async def test_create_board_from_template(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """POST /api/templates/:id/create-board creates a goal and board."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "Reusable", "public")

    resp = await auth_client.post(
        f"/api/templates/{created['id']}/create-board",
        json={"title": "My New Board"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My New Board"
    assert data["board_id"]
    assert data["goal_id"]

    # Verify the board exists with tasks
    board_resp = await auth_client.get(f"/api/boards/{data['board_id']}")
    assert board_resp.status_code == 200
    board_data = board_resp.json()
    assert len(board_data["tasks"]) == 3
    assert len(board_data["edges"]) == 2

    # All tasks should be not_started
    for task in board_data["tasks"]:
        assert task["status"] == "not_started"


@pytest.mark.asyncio
async def test_create_board_from_template_default_title(
    auth_client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """POST /api/templates/:id/create-board uses template title by default."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "Default Title", "public")

    resp = await auth_client.post(
        f"/api/templates/{created['id']}/create-board",
        json={},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Default Title"


@pytest.mark.asyncio
async def test_create_board_from_private_template_by_other_user_rejected(
    auth_client: AsyncClient,
    client: AsyncClient,
    session: AsyncSession,
    answered_goal: Goal,
) -> None:
    """POST /api/templates/:id/create-board for private template returns 404."""
    board, _ = await _create_board_with_tasks(session, answered_goal)
    created = await _create_template(auth_client, board.id, "Private", "private")

    other_user = User(
        email="other4@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(other_user)
    await session.commit()
    await session.refresh(other_user)
    client.cookies.set("access_token", create_access_token(other_user.id))

    resp = await client.post(
        f"/api/templates/{created['id']}/create-board",
        json={},
    )
    assert resp.status_code == 404
