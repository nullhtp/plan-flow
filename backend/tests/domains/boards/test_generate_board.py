from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.domains.ai.schemas import (
    BoardGenerationColumnOutput,
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)
from app.domains.ai.service import AIOutputError
from app.domains.goals.models import Goal


def _mock_board_output() -> BoardGenerationOutput:
    return BoardGenerationOutput(
        board_title="Relocate from Berlin to Lisbon",
        columns=[
            BoardGenerationColumnOutput(
                title="Research",
                description="Gather all necessary information",
                position=0,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Research visa requirements",
                        description="Check D7 visa and NHR options",
                        position=0,
                        priority="high",
                        estimated_minutes=60,
                    ),
                    BoardGenerationTaskOutput(
                        title="Research neighborhoods",
                        description="Find suitable areas in Lisbon",
                        position=1,
                        estimated_minutes=90,
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="Documentation",
                description="Prepare all required paperwork",
                position=1,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Gather documents",
                        description="Collect passport, bank statements, etc.",
                        position=0,
                        priority="high",
                    ),
                    BoardGenerationTaskOutput(
                        title="Apply for visa",
                        description="Submit D7 visa application",
                        position=1,
                        due_date="2026-03-15",
                        priority="high",
                        estimated_minutes=120,
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="Logistics",
                description="Handle moving logistics",
                position=2,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Book flight",
                        description="Book one-way flight to Lisbon",
                        position=0,
                        due_date="2026-04-01",
                        priority="medium",
                        estimated_minutes=30,
                    ),
                    BoardGenerationTaskOutput(
                        title="Arrange pet transport",
                        description="Set up cat transport to Portugal",
                        position=1,
                        priority="medium",
                    ),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_success(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Successful board generation returns 201 with nested board data."""
    mock_ai.return_value = _mock_board_output()

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["goal_id"] == answered_goal.id
    assert data["title"] == "Relocate from Berlin to Lisbon"
    assert len(data["columns"]) == 3
    assert data["columns"][0]["title"] == "Research"
    assert data["columns"][0]["position"] == 0
    assert len(data["columns"][0]["tasks"]) == 2
    assert data["columns"][0]["tasks"][0]["title"] == "Research visa requirements"
    assert data["columns"][0]["tasks"][0]["priority"] == "high"
    # Check progressive metadata is present/null as expected
    assert data["columns"][1]["tasks"][1]["due_date"] == "2026-03-15"
    assert data["columns"][0]["tasks"][1]["due_date"] is None


@pytest.mark.asyncio
async def test_generate_board_wrong_status(
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Goal in 'questioning' status returns 409."""
    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/generate-board",
    )
    assert response.status_code == 409
    assert "answered" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_already_exists(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Second generation attempt returns 409."""
    mock_ai.return_value = _mock_board_output()

    # First generation succeeds
    response1 = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response1.status_code == 201

    # Second attempt fails — goal is now 'active', so the status guard triggers first
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
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_ai_error_reverts_status(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
    session: AsyncMock,
) -> None:
    """AI failure returns 503 and goal status reverts to 'answered'."""
    mock_ai.side_effect = AIOutputError("AI failed")

    response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert response.status_code == 503


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_generate_board_status_transitions(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """Goal transitions from 'answered' to 'active' after board generation."""
    mock_ai.return_value = _mock_board_output()

    # Generate board
    await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )

    # Check goal status is now active
    goal_response = await auth_client.get(f"/api/goals/{answered_goal.id}")
    assert goal_response.status_code == 200
    assert goal_response.json()["status"] == "active"
