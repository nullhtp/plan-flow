"""Integration tests for the template generation API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.domains.ai.schemas import (
    TemplateGenerationOutput,
    TemplateGenSubtaskOutput,
    TemplateGenTaskOutput,
)
from app.domains.auth.models import User
from app.domains.templates.models import TemplateCategory

# ── Helpers ──────────────────────────────────────────────


async def _seed_categories(session: AsyncSession) -> list[TemplateCategory]:
    categories = [
        TemplateCategory(name="Travel", slug="travel", display_order=1),
        TemplateCategory(name="Other", slug="other", display_order=10),
    ]
    session.add_all(categories)
    await session.commit()
    for c in categories:
        await session.refresh(c)
    return categories


def _mock_generation_output() -> TemplateGenerationOutput:
    """Build a valid mock TemplateGenerationOutput."""
    return TemplateGenerationOutput(
        reasoning="Test reasoning",
        suggested_title="Test Template",
        suggested_description="A test template",
        suggested_category_slug="travel",
        tasks=[
            TemplateGenTaskOutput(
                id="t1",
                title="Task 1",
                description="First task",
                depends_on=[],
                is_goal_node=False,
                subtasks=[TemplateGenSubtaskOutput(title="Subtask 1a")],
            ),
            TemplateGenTaskOutput(
                id="t2",
                title="Task 2",
                description="Second task",
                depends_on=["t1"],
                is_goal_node=False,
                subtasks=[],
            ),
            TemplateGenTaskOutput(
                id="t3",
                title="Goal",
                description="Complete the goal",
                depends_on=["t2"],
                is_goal_node=True,
                subtasks=[],
            ),
        ],
    )


# ── Extract Content Endpoint ─────────────────────────────


class TestExtractContentEndpoint:
    async def test_extract_txt_file(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)
        content = (
            "This is enough text content for extraction"
            " to work properly and pass validation."
        )
        response = await client.post(
            "/api/templates/extract-content/file",
            files={"file": ("test.txt", content.encode(), "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "file"
        assert data["source_name"] == "test.txt"
        assert data["char_count"] > 0

    async def test_extract_unsupported_file(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)
        response = await client.post(
            "/api/templates/extract-content/file",
            files={"file": ("test.exe", b"data", "application/octet-stream")},
        )
        assert response.status_code == 422

    async def test_extract_file_too_short(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)
        response = await client.post(
            "/api/templates/extract-content/file",
            files={"file": ("tiny.txt", b"hi", "text/plain")},
        )
        assert response.status_code == 422


# ── Generate Template Endpoint ───────────────────────────


class TestGenerateTemplateEndpoint:
    @patch("app.domains.ai.service.generate_template_from_content")
    async def test_generate_template(
        self,
        mock_generate: AsyncMock,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        await _seed_categories(session)
        mock_generate.return_value = _mock_generation_output()
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/generate",
            json={
                "content": (
                    "Steps to plan a vacation: book flights,"
                    " find hotel, plan activities, pack bags"
                ),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["suggested_title"] == "Test Template"
        assert data["task_count"] == 3
        assert len(data["tasks"]) == 3

    async def test_generate_content_too_short(
        self,
        client: AsyncClient,
        test_user: User,
    ) -> None:
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)
        response = await client.post(
            "/api/templates/generate",
            json={"content": "short"},
        )
        assert response.status_code == 422


# ── Save Generated Template Endpoint ─────────────────────


class TestSaveGeneratedTemplateEndpoint:
    async def test_save_generated_template(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        categories = await _seed_categories(session)
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/save-generated",
            json={
                "title": "My Generated Template",
                "description": "From text",
                "category_id": categories[0].id,
                "visibility": "private",
                "tasks": [
                    {
                        "title": "Task 1",
                        "description": "First",
                        "is_goal_node": False,
                        "depends_on": [],
                        "subtasks": [{"title": "Sub 1"}],
                    },
                    {
                        "title": "Task 2",
                        "description": "Second",
                        "is_goal_node": False,
                        "depends_on": ["t0"],
                        "subtasks": [],
                    },
                    {
                        "title": "Goal",
                        "description": "Done",
                        "is_goal_node": True,
                        "depends_on": ["t1"],
                        "subtasks": [],
                    },
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Generated Template"
        assert data["task_count"] == 3
        assert len(data["tasks"]) == 3
        assert len(data["edges"]) == 2

    async def test_save_with_cycle_rejected(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        await _seed_categories(session)
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/save-generated",
            json={
                "title": "Cyclic Template",
                "tasks": [
                    {
                        "title": "A",
                        "description": "",
                        "is_goal_node": False,
                        "depends_on": ["t1"],
                        "subtasks": [],
                    },
                    {
                        "title": "B",
                        "description": "",
                        "is_goal_node": True,
                        "depends_on": ["t0"],
                        "subtasks": [],
                    },
                ],
            },
        )
        assert response.status_code == 422

    async def test_save_without_goal_node_rejected(
        self,
        client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        await _seed_categories(session)
        token = create_access_token(test_user.id)
        client.cookies.set("access_token", token)

        response = await client.post(
            "/api/templates/save-generated",
            json={
                "title": "No Goal Template",
                "tasks": [
                    {
                        "title": "Task 1",
                        "description": "",
                        "is_goal_node": False,
                        "depends_on": [],
                        "subtasks": [],
                    },
                ],
            },
        )
        assert response.status_code == 422
