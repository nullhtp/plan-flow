from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.domains.ai.schemas import (
    ClassificationOutput,
    QuestionItem,
    ReadinessAssessment,
)
from app.domains.ai.service import AIOutputError, ClassifyAndGenerateResult


def _mock_success_result() -> ClassifyAndGenerateResult:
    return ClassifyAndGenerateResult(
        classification=ClassificationOutput(
            domain="relocation",
            complexity=4,
            confidence=0.9,
            dimensions=["timeline", "budget", "housing"],
            suggested_title="Relocate to Lisbon",
            rejection_reason=None,
            refinement_suggestions=[],
        ),
        questions=[
            QuestionItem(
                id="q1",
                text="What is your budget?",
                type="select",
                options=["< 5000", "5000-10000", "> 10000"],
                rationale="Budget determines housing options",
                required=True,
            ),
            QuestionItem(
                id="q2",
                text="When do you plan to move?",
                type="text",
                options=["1-2 months", "3-4 months", "5-6 months"],
                rationale="Timeline affects planning",
                required=True,
            ),
            QuestionItem(
                id="q3",
                text="Do you have a job lined up?",
                type="select",
                options=["Yes", "No", "Remote work"],
                rationale="Employment affects visa",
                required=True,
            ),
        ],
        is_rejected=False,
        readiness=ReadinessAssessment(
            score=0.0,
            covered_dimensions=[],
            uncovered_dimensions=["timeline", "budget", "housing"],
            summary="No answers collected yet.",
        ),
    )


def _mock_rejection_result() -> ClassifyAndGenerateResult:
    return ClassifyAndGenerateResult(
        classification=ClassificationOutput(
            domain="unknown",
            complexity=1,
            confidence=0.1,
            dimensions=[],
            suggested_title="Be Happier",
            rejection_reason="This goal is too vague to create a plan.",
            refinement_suggestions=[
                "Practice meditation for 10 minutes daily for 30 days",
                "Start a gratitude journal for 2 weeks",
            ],
        ),
        questions=[],
        is_rejected=True,
        rejection_reason="This goal is too vague to create a plan.",
        refinement_suggestions=[
            "Practice meditation for 10 minutes daily for 30 days",
            "Start a gratitude journal for 2 weeks",
        ],
    )


@pytest.mark.asyncio
@patch("app.domains.goals.service.classify_and_generate_questions")
async def test_create_goal_success(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
) -> None:
    """Successful goal creation returns 201 with questions."""
    mock_ai.return_value = _mock_success_result()

    response = await auth_client.post(
        "/api/goals",
        json={"original_input": "Move from Berlin to Lisbon within 3 months"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "goal_id" in data
    assert data["title"] == "Relocate to Lisbon"
    assert data["status"] == "questioning"
    assert len(data["questions"]) == 3
    assert data["questions"][0]["id"] == "q1"
    assert data["questions"][0]["type"] == "select"
    assert data["questions"][0]["rationale"] is not None


@pytest.mark.asyncio
@patch("app.domains.goals.service.classify_and_generate_questions")
async def test_create_goal_rejected_vague(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
) -> None:
    """Vague goal returns 422 with rejection reason and suggestions."""
    mock_ai.return_value = _mock_rejection_result()

    response = await auth_client.post(
        "/api/goals",
        json={"original_input": "be happier"},
    )
    assert response.status_code == 422
    data = response.json()["detail"]
    assert "rejection_reason" in data
    assert "refinement_suggestions" in data
    assert len(data["refinement_suggestions"]) >= 1


@pytest.mark.asyncio
async def test_create_goal_unauthenticated(client: AsyncClient) -> None:
    """Unauthenticated request returns 401."""
    response = await client.post(
        "/api/goals",
        json={"original_input": "Move to Lisbon"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@patch("app.domains.goals.service.classify_and_generate_questions")
async def test_create_goal_ai_error(
    mock_ai: AsyncMock,
    auth_client: AsyncClient,
) -> None:
    """AI failure returns 503."""
    mock_ai.side_effect = AIOutputError("AI failed")

    response = await auth_client.post(
        "/api/goals",
        json={"original_input": "Move to Lisbon"},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_create_goal_empty_input(auth_client: AsyncClient) -> None:
    """Empty input returns 422 validation error."""
    response = await auth_client.post(
        "/api/goals",
        json={"original_input": ""},
    )
    assert response.status_code == 422
