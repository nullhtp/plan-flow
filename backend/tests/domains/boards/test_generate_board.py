"""Integration tests for board generation endpoint (two-step: skeleton + enrichment)."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.goals.models import Goal


def _format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a Server-Sent Event string (mirrors ai/service.py helper)."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def _mock_stream_success(
    **kwargs: Any,
) -> AsyncGenerator[str, None]:
    """Yield SSE events simulating a successful skeleton + enrichment flow."""
    yield _format_sse_event(
        "skeleton_ready",
        {
            "board_title": "Relocate from Berlin to Lisbon",
            "tasks": [
                {
                    "id": "t1",
                    "title": "Research visa requirements",
                    "depends_on": [],
                    "is_goal_node": False,
                },
                {
                    "id": "t2",
                    "title": "Research neighborhoods",
                    "depends_on": [],
                    "is_goal_node": False,
                },
                {
                    "id": "t3",
                    "title": "Gather documents",
                    "depends_on": ["t1"],
                    "is_goal_node": False,
                },
                {
                    "id": "t4",
                    "title": "Apply for visa",
                    "depends_on": ["t3"],
                    "is_goal_node": False,
                },
                {
                    "id": "t5",
                    "title": "Book flight",
                    "depends_on": ["t4", "t2"],
                    "is_goal_node": True,
                },
            ],
            "edges": [
                {"source": "t1", "target": "t3"},
                {"source": "t3", "target": "t4"},
                {"source": "t4", "target": "t5"},
                {"source": "t2", "target": "t5"},
            ],
        },
    )
    # Yield enrichments for each task
    for tid in ["t1", "t2", "t3", "t4", "t5"]:
        yield _format_sse_event(
            "task_enriched",
            {
                "task_id": tid,
                "description": f"Description for {tid}",
                "due_date": None,
                "priority": "high" if tid == "t1" else None,
                "estimated_minutes": 60 if tid == "t1" else None,
                "subtasks": [{"title": f"Subtask 1 for {tid}"}],
            },
        )
    yield _format_sse_event(
        "generation_complete",
        {"board_title": "Relocate from Berlin to Lisbon", "failed_tasks": []},
    )


async def _mock_stream_error(**kwargs: Any) -> AsyncGenerator[str, None]:
    """Yield a generation_error SSE event."""
    yield _format_sse_event(
        "generation_error",
        {
            "error": "skeleton_generation_failed",
            "message": "Board skeleton generation failed after 3 attempts",
            "detail": "AI failed",
        },
    )


@pytest.mark.asyncio
@patch("app.domains.ai.service.generate_board_stream")
async def test_generate_board_success(
    mock_stream: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Successful board generation returns 201 with BoardResponse JSON."""
    mock_stream.side_effect = lambda **kwargs: _mock_stream_success()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Relocate from Berlin to Lisbon"
    assert data["goal_id"] == answered_goal.id
    assert len(data["tasks"]) == 5
    assert len(data["edges"]) >= 4

    # Check tasks have enrichment data
    task_t1 = next(
        t for t in data["tasks"] if t["title"] == "Research visa requirements"
    )
    assert task_t1["description"] == "Description for t1"
    assert task_t1["priority"] == "high"
    assert task_t1["estimated_minutes"] == 60
    assert len(task_t1["subtasks"]) == 1
    assert task_t1["subtasks"][0]["title"] == "Subtask 1 for t1"

    # Check goal node
    goal_tasks = [t for t in data["tasks"] if t["is_goal_node"]]
    assert len(goal_tasks) == 1
    assert goal_tasks[0]["title"] == "Book flight"

    # Board should not be completed yet
    assert data["is_completed"] is False


@pytest.mark.asyncio
async def test_generate_board_wrong_status(
    auth_client: AsyncClient,
    test_goal: Goal,
    session: AsyncSession,
) -> None:
    """Goal in 'active' status returns 409."""
    from app.domains.goals.models import GoalStatus

    # The endpoint now accepts 'questioning' and 'answered'.
    # Set goal to 'active' to trigger the rejection.
    test_goal.status = GoalStatus.ACTIVE.value
    session.add(test_goal)
    await session.commit()

    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/generate-board",
    )
    assert response.status_code == 409


@pytest.mark.asyncio
@patch("app.domains.ai.service.generate_board_stream")
async def test_generate_board_already_exists(
    mock_stream: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncSession,
) -> None:
    """Second generation attempt returns 409."""
    mock_stream.side_effect = lambda **kwargs: _mock_stream_success()

    # First generation succeeds
    response1 = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response1.status_code == 201

    # Second attempt fails — goal is now active / board exists
    response2 = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response2.status_code == 409


@pytest.mark.asyncio
async def test_generate_board_not_found(
    auth_client: AsyncClient,
) -> None:
    """Non-existent goal returns 404."""
    response = await auth_client.post(
        "/api/goals/nonexistent-id/generate-board",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_board_unauthenticated(
    client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Unauthenticated request returns 401."""
    response = await client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@patch("app.domains.ai.service.generate_board_stream")
async def test_generate_board_ai_error_returns_500(
    mock_stream: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """AI failure returns 500 with error message."""
    mock_stream.side_effect = lambda **kwargs: _mock_stream_error()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 500
    assert "failed" in response.json()["detail"].lower()


@pytest.mark.asyncio
@patch("app.domains.ai.service.generate_board_stream")
async def test_generate_board_status_transitions(
    mock_stream: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Goal transitions from 'answered' to 'active' after successful board generation."""  # noqa: E501
    mock_stream.return_value = _mock_stream_success()

    # Generate board
    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 201

    # Check goal status is now active
    goal_response = await auth_client.get(f"/api/goals/{answered_goal.id}")
    assert goal_response.status_code == 200
    assert goal_response.json()["status"] == "active"


@pytest.mark.asyncio
@patch("app.domains.ai.service.generate_board_stream")
async def test_generate_board_has_edges(
    mock_stream: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Generated board includes dependency edges."""
    mock_stream.return_value = _mock_stream_success()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 201

    data = response.json()
    edges = data["edges"]
    assert len(edges) >= 4  # t1->t3, t3->t4, t4->t5, t2->t5
    for edge in edges:
        assert "source" in edge
        assert "target" in edge

    # Verify edges reference valid task IDs
    task_ids = {t["id"] for t in data["tasks"]}
    for edge in edges:
        assert edge["source"] in task_ids
        assert edge["target"] in task_ids


@pytest.mark.asyncio
@patch("app.domains.ai.service.generate_board_stream")
async def test_generate_board_persists_to_db(
    mock_stream: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Board and tasks are persisted to DB and retrievable via GET."""
    mock_stream.return_value = _mock_stream_success()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 201
    board_id = response.json()["id"]

    # Retrieve board via GET endpoint
    get_response = await auth_client.get(f"/api/boards/{board_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["title"] == "Relocate from Berlin to Lisbon"
    assert len(data["tasks"]) == 5
    assert len(data["edges"]) >= 4

    # Check enrichment was persisted
    task_t1 = next(
        t for t in data["tasks"] if t["title"] == "Research visa requirements"
    )
    assert task_t1["description"] == "Description for t1"
    assert task_t1["priority"] == "high"
    assert task_t1["estimated_minutes"] == 60
    assert len(task_t1["subtasks"]) == 1
    assert task_t1["subtasks"][0]["title"] == "Subtask 1 for t1"


@pytest.mark.asyncio
@patch("app.domains.ai.service.generate_board_stream")
async def test_generate_board_ai_error_reverts_goal(
    mock_stream: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """AI failure reverts goal back to 'questioning' status."""
    mock_stream.return_value = _mock_stream_error()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 500

    # Goal should be reverted to 'questioning' so user can retry
    goal_response = await auth_client.get(f"/api/goals/{answered_goal.id}")
    assert goal_response.status_code == 200
    assert goal_response.json()["status"] == "questioning"
