from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.schemas import QuestionItem, QuestionsOutput, ReadinessAssessment
from app.domains.goals.models import Goal


@pytest.mark.asyncio
@patch("app.domains.goals.service.generate_follow_up_questions")
async def test_submit_answers_round1_with_followups(
    mock_followup: AsyncMock,
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Round 1 answers with follow-up questions returns them."""
    mock_followup.return_value = QuestionsOutput(
        questions=[
            QuestionItem(
                id="r2q1",
                text="Do you have pets to relocate?",
                type="select",
                options=["Yes", "No", "Not applicable"],
                rationale="Pet transport requires extra planning",
                required=True,
            ),
        ],
        readiness=ReadinessAssessment(
            score=0.5,
            covered_dimensions=["budget"],
            uncovered_dimensions=["timeline", "housing"],
            summary="More information needed.",
        ),
    )

    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/answers",
        json={
            "answers": {"q1": "5000-10000", "q2": "Remote work", "q3": "None"},
            "round": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["next_questions"]) == 1
    assert data["next_questions"][0]["id"] == "r2q1"
    assert data["status"] == "questioning"


@pytest.mark.asyncio
@patch("app.domains.goals.service.generate_follow_up_questions")
async def test_submit_answers_round1_no_followups(
    mock_followup: AsyncMock,
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Round 1 answers without follow-ups returns empty next_questions."""
    mock_followup.return_value = QuestionsOutput(
        questions=[],
        readiness=ReadinessAssessment(
            score=0.9,
            covered_dimensions=["timeline", "budget", "housing"],
            uncovered_dimensions=[],
            summary="Sufficient information collected.",
        ),
    )

    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/answers",
        json={
            "answers": {"q1": "5000-10000", "q2": "Remote work", "q3": "None"},
            "round": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["next_questions"]) == 0
    # Goal stays in 'questioning' — user decides when to generate
    assert data["status"] == "questioning"


@pytest.mark.asyncio
@patch("app.domains.goals.service.generate_follow_up_questions")
async def test_submit_answers_round2_completes(
    mock_followup: AsyncMock,
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Round 2 answers returns next_questions (possibly empty)."""
    mock_followup.return_value = None

    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/answers",
        json={
            "answers": {"fq1": "Yes"},
            "round": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["next_questions"] == []
    # Goal stays in 'questioning'
    assert data["status"] == "questioning"


@pytest.mark.asyncio
async def test_submit_answers_wrong_status(
    auth_client: AsyncClient,
    test_goal: Goal,
    session: AsyncSession,
) -> None:
    """Answers for a goal not in questioning status returns 409."""
    test_goal.status = "answered"
    session.add(test_goal)
    await session.commit()

    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/answers",
        json={"answers": {"q1": "value"}, "round": 1},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_submit_answers_not_found(
    auth_client: AsyncClient,
) -> None:
    """Answers for non-existent goal returns 404."""
    response = await auth_client.post(
        "/api/goals/nonexistent-id/answers",
        json={"answers": {"q1": "value"}, "round": 1},
    )
    assert response.status_code == 404
