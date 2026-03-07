"""Integration tests for template classification and answers endpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.core.security import create_access_token
from app.domains.ai.schemas import (
    ClassificationOutput,
    QuestionItem,
    QuestionsOutput,
    ReadinessAssessment,
)
from app.domains.auth.models import User

# ── Helpers ──────────────────────────────────────────────


def _mock_classification(
    confidence: float = 0.85,
) -> ClassificationOutput:
    return ClassificationOutput(
        reasoning="Test reasoning",
        domain="project-management",
        complexity=3,
        confidence=confidence,
        dimensions=["scope", "timeline", "resources"],
        suggested_title="SaaS Product Launch",
        language="en",
        rejection_reason="Too vague" if confidence < 0.3 else None,
        refinement_suggestions=["Be more specific"] if confidence < 0.3 else [],
    )


def _mock_questions_output() -> QuestionsOutput:
    return QuestionsOutput(
        reasoning="Need more context",
        questions=[
            QuestionItem(
                id="q1",
                text="What type of project?",
                type="select",
                options=["Web app", "Mobile app", "API", "Other"],
                rationale="Helps scope the template",
                required=True,
                allow_other=True,
            ),
            QuestionItem(
                id="q2",
                text="Expected timeline?",
                type="select",
                options=["1 week", "2 weeks", "1 month", "3 months"],
                rationale="Helps set milestones",
                required=True,
                allow_other=True,
            ),
            QuestionItem(
                id="q3",
                text="Team size?",
                type="number",
                options=["1-2", "3-5", "6-10", "10+"],
                rationale="Affects task breakdown",
                required=False,
                allow_other=True,
            ),
        ],
        readiness=ReadinessAssessment(
            score=0.4,
            covered_dimensions=["scope"],
            uncovered_dimensions=["timeline", "resources"],
            summary="Need more details about timeline and resources.",
        ),
    )


# ── Classify Endpoint Tests ──────────────────────────────


class TestTemplateClassifyEndpoint:
    @patch("app.domains.ai.service.generate_template_questions")
    @patch("app.domains.ai.service.classify_template_content")
    async def test_classify_describe_input(
        self,
        mock_classify: AsyncMock,
        mock_questions: AsyncMock,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Classify a description input returns classification + questions."""
        mock_classify.return_value = _mock_classification()
        mock_questions.return_value = _mock_questions_output()

        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/classify",
            json={
                "input_type": "describe",
                "content": "A template for launching a SaaS product",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["classification"]["domain"] == "project-management"
        assert data["classification"]["suggested_title"] == "SaaS Product Launch"
        assert data["classification"]["confidence"] == 0.85
        assert len(data["questions"]) == 3
        assert data["questions"][0]["id"] == "q1"
        assert data["is_rejected"] is False

    @patch("app.domains.ai.service.classify_template_content")
    async def test_classify_rejected_input(
        self,
        mock_classify: AsyncMock,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Low-confidence classification results in rejection."""
        mock_classify.return_value = _mock_classification(confidence=0.2)

        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/classify",
            json={
                "input_type": "describe",
                "content": "something vague",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["is_rejected"] is True
        assert data["rejection_reason"] is not None
        assert len(data["questions"]) == 0

    @patch("app.domains.ai.service.generate_template_questions")
    @patch("app.domains.ai.service.classify_template_content")
    async def test_classify_with_title_hint(
        self,
        mock_classify: AsyncMock,
        mock_questions: AsyncMock,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Providing a title hint passes it through."""
        mock_classify.return_value = _mock_classification()
        mock_questions.return_value = _mock_questions_output()

        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/classify",
            json={
                "input_type": "text",
                "content": "Step 1: Research. Step 2: Plan. Step 3: Execute.",
                "title": "My Custom Title",
            },
        )
        assert response.status_code == 200
        assert response.json()["is_rejected"] is False

    async def test_classify_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated request returns 401."""
        response = await client.post(
            "/api/templates/classify",
            json={
                "input_type": "describe",
                "content": "A template for something",
            },
        )
        assert response.status_code == 401

    async def test_classify_empty_content(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Empty content is rejected by validation."""
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/classify",
            json={
                "input_type": "describe",
                "content": "",
            },
        )
        assert response.status_code == 422


# ── Answers Endpoint Tests ───────────────────────────────


class TestTemplateAnswersEndpoint:
    @patch("app.domains.ai.service.generate_template_follow_up_questions")
    async def test_submit_round_1_answers(
        self,
        mock_follow_up: AsyncMock,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Round 1 answers trigger follow-up question generation."""
        mock_follow_up.return_value = _mock_questions_output()

        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/answers",
            json={
                "answers": {"q1": "Web app", "q2": "1 month"},
                "round": 1,
                "classification": {
                    "domain": "project-management",
                    "complexity": 3,
                    "confidence": 0.85,
                    "dimensions": ["scope", "timeline", "resources"],
                    "suggested_title": "SaaS Product Launch",
                    "language": "en",
                },
                "previous_rounds": [
                    {
                        "round": 1,
                        "questions": [
                            {
                                "id": "q1",
                                "text": "What type?",
                                "type": "select",
                                "options": ["Web app", "Mobile", "API", "Other"],
                            },
                            {
                                "id": "q2",
                                "text": "Timeline?",
                                "type": "select",
                                "options": ["1 week", "2 weeks", "1 month", "3 months"],
                            },
                        ],
                        "answers": {"q1": "Web app", "q2": "1 month"},
                    },
                ],
                "raw_input": "A template for launching a SaaS product",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["next_round"] == 2
        assert len(data["next_questions"]) > 0
        assert data["is_ready"] is False

    async def test_submit_round_2_answers_auto_ready(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Round 2 answers automatically mark as ready (max 1 follow-up)."""
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/answers",
            json={
                "answers": {"q3": "3-5"},
                "round": 2,
                "classification": {
                    "domain": "project-management",
                    "complexity": 3,
                    "confidence": 0.85,
                    "dimensions": ["scope", "timeline", "resources"],
                    "suggested_title": "SaaS Product Launch",
                    "language": "en",
                },
                "previous_rounds": [],
                "raw_input": "A template for launching a SaaS product",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["is_ready"] is True
        assert len(data["next_questions"]) == 0
        assert data["next_round"] == 3

    async def test_submit_answers_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated request returns 401."""
        response = await client.post(
            "/api/templates/answers",
            json={
                "answers": {"q1": "test"},
                "round": 1,
                "classification": {
                    "domain": "test",
                    "complexity": 1,
                    "confidence": 0.8,
                    "dimensions": [],
                    "suggested_title": "Test",
                    "language": "en",
                },
                "raw_input": "test input",
            },
        )
        assert response.status_code == 401


# ── Streaming Endpoint Tests ─────────────────────────────


def _format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def _mock_template_stream_success(
    **kwargs: Any,
) -> AsyncGenerator[str, None]:
    """Yield SSE events for a successful template generation."""
    yield _format_sse_event(
        "skeleton_ready",
        {
            "board_title": "SaaS Product Launch Template",
            "tasks": [
                {
                    "id": "t1",
                    "title": "Market Research",
                    "depends_on": [],
                    "is_goal_node": False,
                },
                {
                    "id": "t2",
                    "title": "Define MVP",
                    "depends_on": ["t1"],
                    "is_goal_node": False,
                },
                {
                    "id": "t3",
                    "title": "Launch Product",
                    "depends_on": ["t2"],
                    "is_goal_node": True,
                },
            ],
            "edges": [
                {"source": "t1", "target": "t2"},
                {"source": "t2", "target": "t3"},
            ],
        },
    )
    for tid in ["t1", "t2", "t3"]:
        yield _format_sse_event(
            "task_enriched",
            {
                "task_id": tid,
                "description": f"Description for {tid}",
                "due_date": None,
                "priority": "high" if tid == "t1" else None,
                "estimated_minutes": 120 if tid == "t1" else None,
                "subtasks": [{"title": f"Sub for {tid}"}],
            },
        )
    yield _format_sse_event(
        "generation_complete",
        {"board_title": "SaaS Product Launch Template", "failed_tasks": []},
    )


async def _mock_template_stream_error(
    **kwargs: Any,
) -> AsyncGenerator[str, None]:
    """Yield a generation_error SSE event."""
    yield _format_sse_event(
        "generation_error",
        {
            "error": "skeleton_generation_failed",
            "message": "Template generation failed after 3 attempts",
        },
    )


class TestTemplateStreamEndpoint:
    @patch("app.domains.ai.service.generate_template_stream")
    async def test_stream_returns_sse(
        self,
        mock_stream: AsyncMock,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        """Stream endpoint returns text/event-stream content type."""
        mock_stream.return_value = _mock_template_stream_success()

        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/generate/stream",
            json={
                "raw_input": "A template for launching a SaaS product",
                "classification": {
                    "domain": "project-management",
                    "complexity": 3,
                    "confidence": 0.85,
                    "dimensions": ["scope", "timeline"],
                    "suggested_title": "SaaS Launch",
                    "language": "en",
                },
                "qa_rounds": [],
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse SSE events from the response body
        body = response.text
        events = []
        for block in body.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            event_type = "message"
            data_str = ""
            for line in block.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data_str = line[6:]
            if data_str:
                events.append((event_type, json.loads(data_str)))

        event_types = [e[0] for e in events]
        assert "skeleton_ready" in event_types
        assert "task_enriched" in event_types
        assert "generation_complete" in event_types

        # Verify skeleton data
        skeleton = next(d for t, d in events if t == "skeleton_ready")
        assert skeleton["board_title"] == "SaaS Product Launch Template"
        assert len(skeleton["tasks"]) == 3

    async def test_stream_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated request returns 401."""
        response = await client.post(
            "/api/templates/generate/stream",
            json={
                "raw_input": "test",
                "classification": {
                    "domain": "test",
                    "complexity": 1,
                    "confidence": 0.8,
                    "dimensions": [],
                    "suggested_title": "Test",
                    "language": "en",
                },
            },
        )
        assert response.status_code == 401
