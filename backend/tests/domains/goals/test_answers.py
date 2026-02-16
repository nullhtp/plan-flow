from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.schemas import QuestionItem
from app.domains.goals.models import Goal


@pytest.mark.asyncio
@patch("app.domains.goals.service.generate_follow_up_questions")
async def test_submit_answers_round1_with_followups(
    mock_followup: AsyncMock,
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Round 1 answers with follow-up questions returns them."""
    mock_followup.return_value = [
        QuestionItem(
            id="fq1",
            text="Do you have pets to relocate?",
            type="select",
            options=["Yes", "No"],
            rationale="Pet transport requires extra planning",
            required=True,
        ),
    ]

    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/answers",
        json={
            "answers": {"q1": "5000-10000", "q2": "Remote work", "q3": "None"},
            "round": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_complete"] is False
    assert len(data["follow_up_questions"]) == 1
    assert data["follow_up_questions"][0]["id"] == "fq1"
    assert data["status"] == "questioning"


@pytest.mark.asyncio
@patch("app.domains.goals.service.generate_follow_up_questions")
async def test_submit_answers_round1_no_followups(
    mock_followup: AsyncMock,
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Round 1 answers without follow-ups completes questioning."""
    mock_followup.return_value = []

    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/answers",
        json={
            "answers": {"q1": "5000-10000", "q2": "Remote work", "q3": "None"},
            "round": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_complete"] is True
    assert len(data["follow_up_questions"]) == 0
    assert data["status"] == "answered"


@pytest.mark.asyncio
async def test_submit_answers_round2_completes(
    auth_client: AsyncClient,
    test_goal: Goal,
) -> None:
    """Round 2 always completes questioning."""
    response = await auth_client.post(
        f"/api/goals/{test_goal.id}/answers",
        json={
            "answers": {"fq1": "Yes"},
            "round": 2,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_complete"] is True
    assert data["status"] == "answered"


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
