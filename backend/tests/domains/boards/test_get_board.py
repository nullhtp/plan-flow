from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.domains.ai.schemas import (
    BoardGenerationColumnOutput,
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)
from app.domains.goals.models import Goal


def _mock_board_output() -> BoardGenerationOutput:
    return BoardGenerationOutput(
        board_title="Relocate from Berlin to Lisbon",
        columns=[
            BoardGenerationColumnOutput(
                title="Research",
                description="Gather information",
                position=0,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Research visa",
                        description="Check visa options",
                        position=0,
                        priority="high",
                    ),
                    BoardGenerationTaskOutput(
                        title="Research areas",
                        description="Find neighborhoods",
                        position=1,
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="Prepare",
                description="Get ready",
                position=1,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Gather docs",
                        description="Collect paperwork",
                        position=0,
                    ),
                    BoardGenerationTaskOutput(
                        title="Apply visa",
                        description="Submit application",
                        position=1,
                        due_date="2026-03-15",
                    ),
                ],
            ),
            BoardGenerationColumnOutput(
                title="Move",
                description="Execute the move",
                position=2,
                tasks=[
                    BoardGenerationTaskOutput(
                        title="Book flight",
                        description="Book ticket",
                        position=0,
                        estimated_minutes=30,
                    ),
                    BoardGenerationTaskOutput(
                        title="Pack belongings",
                        description="Pack everything",
                        position=1,
                    ),
                ],
            ),
        ],
    )


@pytest.mark.asyncio
@patch("app.domains.boards.service.generate_board_from_context")
async def test_get_board_success(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
    answered_goal: Goal,
) -> None:
    """GET board returns nested columns and tasks."""
    mock_ai.return_value = _mock_board_output()

    # Create board first
    create_response = await auth_client.post(
        f"/api/goals/{answered_goal.id}/generate-board",
    )
    assert create_response.status_code == 201
    board_id = create_response.json()["id"]

    # Retrieve board
    response = await auth_client.get(f"/api/boards/{board_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == board_id
    assert data["goal_id"] == answered_goal.id
    assert data["title"] == "Relocate from Berlin to Lisbon"
    assert len(data["columns"]) == 3
    # Verify columns are ordered by position
    positions = [col["position"] for col in data["columns"]]
    assert positions == [0, 1, 2]
    # Verify tasks within columns
    assert len(data["columns"][0]["tasks"]) == 2
    assert data["columns"][0]["tasks"][0]["title"] == "Research visa"


@pytest.mark.asyncio
async def test_get_board_not_found(
    auth_client: AsyncClient,
) -> None:
    """Non-existent board returns 404."""
    response = await auth_client.get("/api/boards/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_board_unauthenticated(
    client: AsyncClient,
) -> None:
    """Unauthenticated request returns 401."""
    response = await client.get("/api/boards/some-id")
    assert response.status_code == 401
