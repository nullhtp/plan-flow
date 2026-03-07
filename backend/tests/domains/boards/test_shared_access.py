"""Integration tests for board sharing.

Covers share links, join, members, and access validation.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.auth.models import User
from app.domains.boards.member_repository import MemberRepository
from app.domains.boards.ownership import get_user_role_for_board
from app.domains.goals.models import Goal
from app.main import app
from tests.conftest import create_test_board

# ── Helpers ──────────────────────────────────────────────


@pytest.fixture
async def other_user(session: AsyncSession) -> User:
    """Create a second user for sharing tests."""
    user = User(email="other@example.com", hashed_password=hash_password("password123"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _make_authed_client(transport: ASGITransport, user: User) -> AsyncClient:
    """Create an authenticated AsyncClient for the given user."""
    client = AsyncClient(transport=transport, base_url="http://test")
    token = create_access_token(user.id)
    client.cookies.set("access_token", token)
    return client


@pytest.fixture
async def transport():
    return ASGITransport(app=app)  # pyright: ignore[reportArgumentType]


@pytest.fixture
async def owner_client(transport: ASGITransport, test_user: User):
    async with _make_authed_client(transport, test_user) as c:
        yield c


@pytest.fixture
async def other_client(transport: ASGITransport, other_user: User):
    async with _make_authed_client(transport, other_user) as c:
        yield c


@pytest.fixture
async def board_with_owner(session: AsyncSession, answered_goal: Goal):
    return await create_test_board(session, answered_goal)


async def _create_share_and_join(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_id: str,
) -> str:
    """Helper: create share link and join as other user. Returns token."""
    share_resp = await owner_client.post(f"/api/boards/{board_id}/share")
    token = share_resp.json()["token"]
    await other_client.post("/api/boards/join", json={"token": token})
    return token


# ── 7.1 Share Link CRUD (owner-only) ────────────────────


@pytest.mark.asyncio
async def test_create_share_link(owner_client: AsyncClient, board_with_owner) -> None:
    board, _ = board_with_owner
    resp = await owner_client.post(f"/api/boards/{board.id}/share")
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert "url" in data
    assert data["token"] in data["url"]


@pytest.mark.asyncio
async def test_get_share_link(owner_client: AsyncClient, board_with_owner) -> None:
    board, _ = board_with_owner
    await owner_client.post(f"/api/boards/{board.id}/share")
    resp = await owner_client.get(f"/api/boards/{board.id}/share")
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_get_share_link_not_found(
    owner_client: AsyncClient, board_with_owner
) -> None:
    board, _ = board_with_owner
    resp = await owner_client.get(f"/api/boards/{board.id}/share")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_share_link(
    owner_client: AsyncClient, board_with_owner
) -> None:
    board, _ = board_with_owner
    resp1 = await owner_client.post(f"/api/boards/{board.id}/share")
    token1 = resp1.json()["token"]
    resp2 = await owner_client.post(f"/api/boards/{board.id}/share")
    token2 = resp2.json()["token"]
    assert token1 != token2


@pytest.mark.asyncio
async def test_delete_share_link(owner_client: AsyncClient, board_with_owner) -> None:
    board, _ = board_with_owner
    await owner_client.post(f"/api/boards/{board.id}/share")
    resp = await owner_client.delete(f"/api/boards/{board.id}/share")
    assert resp.status_code == 204
    resp2 = await owner_client.get(f"/api/boards/{board.id}/share")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_share_link_not_found(
    owner_client: AsyncClient, board_with_owner
) -> None:
    board, _ = board_with_owner
    resp = await owner_client.delete(f"/api/boards/{board.id}/share")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_share_link_non_owner_denied(
    other_client: AsyncClient, board_with_owner
) -> None:
    board, _ = board_with_owner
    resp = await other_client.post(f"/api/boards/{board.id}/share")
    assert resp.status_code == 404


# ── 7.2 Join Endpoint ───────────────────────────────────


@pytest.mark.asyncio
async def test_join_valid_token(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    share_resp = await owner_client.post(f"/api/boards/{board.id}/share")
    token = share_resp.json()["token"]

    join_resp = await other_client.post("/api/boards/join", json={"token": token})
    assert join_resp.status_code == 200
    data = join_resp.json()
    assert data["board_id"] == board.id
    assert data["role"] == "collaborator"


@pytest.mark.asyncio
async def test_join_invalid_token(other_client: AsyncClient) -> None:
    resp = await other_client.post("/api/boards/join", json={"token": "bad-token"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_join_idempotent(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    share_resp = await owner_client.post(f"/api/boards/{board.id}/share")
    token = share_resp.json()["token"]

    resp1 = await other_client.post("/api/boards/join", json={"token": token})
    resp2 = await other_client.post("/api/boards/join", json={"token": token})
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["role"] == resp2.json()["role"] == "collaborator"


@pytest.mark.asyncio
async def test_owner_self_join(
    owner_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    share_resp = await owner_client.post(f"/api/boards/{board.id}/share")
    token = share_resp.json()["token"]

    join_resp = await owner_client.post("/api/boards/join", json={"token": token})
    assert join_resp.status_code == 200
    assert join_resp.json()["role"] == "owner"


# ── 7.3 Member Management ──────────────────────────────


@pytest.mark.asyncio
async def test_list_members_includes_owner(
    owner_client: AsyncClient, board_with_owner
) -> None:
    board, _ = board_with_owner
    resp = await owner_client.get(f"/api/boards/{board.id}/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) >= 1
    roles = [m["role"] for m in members]
    assert "owner" in roles


@pytest.mark.asyncio
async def test_list_members_after_join(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    await _create_share_and_join(owner_client, other_client, board.id)

    resp = await owner_client.get(f"/api/boards/{board.id}/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 2
    roles = {m["role"] for m in members}
    assert roles == {"owner", "collaborator"}


@pytest.mark.asyncio
async def test_revoke_member(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    other_user: User,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    await _create_share_and_join(owner_client, other_client, board.id)

    resp = await owner_client.delete(f"/api/boards/{board.id}/members/{other_user.id}")
    assert resp.status_code == 204

    members_resp = await owner_client.get(f"/api/boards/{board.id}/members")
    assert len(members_resp.json()) == 1


@pytest.mark.asyncio
async def test_cannot_revoke_owner(
    owner_client: AsyncClient,
    test_user: User,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    resp = await owner_client.delete(f"/api/boards/{board.id}/members/{test_user.id}")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_revoke_nonexistent_member(
    owner_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    resp = await owner_client.delete(f"/api/boards/{board.id}/members/nonexistent-id")
    assert resp.status_code == 404


# ── 7.4 Access Validation ──────────────────────────────


@pytest.mark.asyncio
async def test_collaborator_can_view_board(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    await _create_share_and_join(owner_client, other_client, board.id)

    resp = await other_client.get(f"/api/boards/{board.id}")
    assert resp.status_code == 200
    assert resp.json()["role"] == "collaborator"


@pytest.mark.asyncio
async def test_collaborator_can_update_board(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    await _create_share_and_join(owner_client, other_client, board.id)

    resp = await other_client.patch(
        f"/api/boards/{board.id}", json={"title": "Updated by collaborator"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated by collaborator"


@pytest.mark.asyncio
async def test_collaborator_cannot_manage_share(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    await _create_share_and_join(owner_client, other_client, board.id)

    # Collaborator cannot create share links
    resp = await other_client.post(f"/api/boards/{board.id}/share")
    assert resp.status_code == 404

    # Collaborator cannot view share links
    resp = await other_client.get(f"/api/boards/{board.id}/share")
    assert resp.status_code == 404

    # Collaborator cannot delete share links
    resp = await other_client.delete(f"/api/boards/{board.id}/share")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_non_member_cannot_view_board(
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    resp = await other_client.get(f"/api/boards/{board.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_shared_boards_list(
    owner_client: AsyncClient,
    other_client: AsyncClient,
    board_with_owner,
) -> None:
    board, _ = board_with_owner
    await _create_share_and_join(owner_client, other_client, board.id)

    resp = await other_client.get("/api/boards", params={"shared": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == board.id
    assert data[0]["role"] == "collaborator"


@pytest.mark.asyncio
async def test_shared_boards_list_empty_for_owner(
    owner_client: AsyncClient,
    board_with_owner,
) -> None:
    """Owner's shared boards list should be empty (they own, not collaborate)."""
    resp = await owner_client.get("/api/boards", params={"shared": "true"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── 7.5 Ownership unit tests ───────────────────────────


@pytest.mark.asyncio
async def test_get_user_role_owner(
    session: AsyncSession, answered_goal: Goal
) -> None:
    board, _ = await create_test_board(session, answered_goal)
    role = await get_user_role_for_board(session, board.id, answered_goal.user_id)
    assert role == "owner"


@pytest.mark.asyncio
async def test_get_user_role_collaborator(
    session: AsyncSession, answered_goal: Goal, other_user: User
) -> None:
    board, _ = await create_test_board(session, answered_goal)
    repo = MemberRepository(session)
    await repo.create(board.id, other_user.id)
    await session.commit()

    role = await get_user_role_for_board(session, board.id, other_user.id)
    assert role == "collaborator"


@pytest.mark.asyncio
async def test_get_user_role_none(
    session: AsyncSession, answered_goal: Goal, other_user: User
) -> None:
    board, _ = await create_test_board(session, answered_goal)
    role = await get_user_role_for_board(session, board.id, other_user.id)
    assert role is None
