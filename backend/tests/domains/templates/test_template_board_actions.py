"""Tests for AI action generation when creating boards from templates."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.schemas import SubtaskActionOutput
from app.domains.boards.models import Board, Subtask, Task
from app.domains.goals.models import Goal, GoalStatus
from app.domains.templates.models import (
    BoardTemplate,
    TemplateSubtask,
    TemplateTask,
    TemplateTaskDependency,
)
from app.domains.templates.service import generate_board_subtask_actions

# ── Helpers ──────────────────────────────────────────────


async def _create_template_with_subtasks(
    session: AsyncSession,
    user_id: str,
) -> BoardTemplate:
    """Create a template with 2 tasks, each having 2 subtasks."""
    template = BoardTemplate(
        user_id=user_id,
        title="Test Template",
        visibility="public",
        task_count=2,
    )
    session.add(template)
    await session.flush()

    task1 = TemplateTask(
        template_id=template.id,
        title="Research Options",
        description="Research available options",
        is_goal_node=False,
    )
    task2 = TemplateTask(
        template_id=template.id,
        title="Make Decision",
        description="Decide on the best option",
        is_goal_node=True,
    )
    session.add_all([task1, task2])
    await session.flush()

    dep = TemplateTaskDependency(
        template_id=template.id,
        dependent_task_id=task2.id,
        dependency_task_id=task1.id,
    )
    session.add(dep)

    subtasks = [
        TemplateSubtask(
            template_task_id=task1.id, title="Search online", position="a0"
        ),
        TemplateSubtask(template_task_id=task1.id, title="Ask friends", position="a1"),
        TemplateSubtask(
            template_task_id=task2.id, title="Compare prices", position="a0"
        ),
        TemplateSubtask(
            template_task_id=task2.id, title="Visit the office", position="a1"
        ),
    ]
    session.add_all(subtasks)
    await session.commit()
    await session.refresh(template)
    return template


def _make_actions(subtask_titles: list[str]) -> list[SubtaskActionOutput]:
    """Build mock SubtaskActionOutput list for the given titles."""
    actions: list[SubtaskActionOutput] = []
    for title in subtask_titles:
        # "Visit the office" is a physical task — not automatable
        if "visit" in title.lower() or "ask" in title.lower():
            actions.append(
                SubtaskActionOutput(
                    subtask_title=title,
                    action_label=None,
                    action_icon=None,
                    action_prompt=None,
                )
            )
        else:
            actions.append(
                SubtaskActionOutput(
                    subtask_title=title,
                    action_label=f"AI: {title}",
                    action_icon="research",
                    action_prompt=f"Help me with: {title}",
                )
            )
    return actions


# ── Unit Tests: generate_board_subtask_actions ───────────


@pytest.mark.asyncio
async def test_generate_board_subtask_actions_populates_fields(
    session: AsyncSession,
    test_user: User,  # noqa: F821
) -> None:
    """Actions are generated and persisted for automatable subtasks."""

    # Create a goal + board + tasks + subtasks directly in the DB
    goal = Goal(
        user_id=test_user.id,
        title="Test Goal",
        original_input="test",
        status=GoalStatus.ACTIVE.value,
        ai_context={},
    )
    session.add(goal)
    await session.flush()

    board = Board(goal_id=goal.id, title="Test Board")
    session.add(board)
    await session.flush()

    task1 = Task(
        board_id=board.id,
        title="Research Options",
        description="Research stuff",
        status="not_started",
        is_goal_node=False,
    )
    task2 = Task(
        board_id=board.id,
        title="Make Decision",
        description="Decide stuff",
        status="not_started",
        is_goal_node=True,
    )
    session.add_all([task1, task2])
    await session.flush()

    subtask1 = Subtask(task_id=task1.id, title="Search online", position="a0")
    subtask2 = Subtask(task_id=task1.id, title="Ask friends", position="a1")
    subtask3 = Subtask(task_id=task2.id, title="Compare prices", position="a0")
    subtask4 = Subtask(task_id=task2.id, title="Visit the office", position="a1")
    session.add_all([subtask1, subtask2, subtask3, subtask4])
    await session.commit()

    # Mock generate_subtask_actions to return deterministic results
    def mock_generate(
        task_title: str,
        task_description: str,
        task_status: str,
        subtasks: list[dict[str, str]],
        **kwargs: object,
    ) -> list[SubtaskActionOutput]:
        titles = [s["title"] for s in subtasks]
        return _make_actions(titles)

    mock = AsyncMock(side_effect=mock_generate)

    with patch(
        "app.domains.ai.service.generate_subtask_actions",
        mock,
    ):
        await generate_board_subtask_actions(
            session,
            board_id=board.id,
            user_id=test_user.id,
        )

    # Verify: 2 LLM calls (one per task with subtasks)
    assert mock.call_count == 2

    # Refresh subtasks to see updated values
    await session.refresh(subtask1)
    await session.refresh(subtask2)
    await session.refresh(subtask3)
    await session.refresh(subtask4)

    # "Search online" → automatable
    assert subtask1.action_label == "AI: Search online"
    assert subtask1.action_icon == "research"
    assert subtask1.action_prompt == "Help me with: Search online"

    # "Ask friends" → not automatable (physical)
    assert subtask2.action_label is None

    # "Compare prices" → automatable
    assert subtask3.action_label == "AI: Compare prices"

    # "Visit the office" → not automatable (physical)
    assert subtask4.action_label is None


@pytest.mark.asyncio
async def test_generate_board_subtask_actions_graceful_degradation(
    session: AsyncSession,
    test_user: User,  # noqa: F821
) -> None:
    """If one task's LLM call fails, other tasks still get actions."""
    goal = Goal(
        user_id=test_user.id,
        title="Test Goal",
        original_input="test",
        status=GoalStatus.ACTIVE.value,
        ai_context={},
    )
    session.add(goal)
    await session.flush()

    board = Board(goal_id=goal.id, title="Test Board")
    session.add(board)
    await session.flush()

    task1 = Task(
        board_id=board.id,
        title="Task That Fails",
        description="This will fail",
        status="not_started",
        is_goal_node=False,
    )
    task2 = Task(
        board_id=board.id,
        title="Task That Succeeds",
        description="This will succeed",
        status="not_started",
        is_goal_node=True,
    )
    session.add_all([task1, task2])
    await session.flush()

    subtask_fail = Subtask(task_id=task1.id, title="Failing subtask", position="a0")
    subtask_ok = Subtask(task_id=task2.id, title="Analyze results", position="a0")
    session.add_all([subtask_fail, subtask_ok])
    await session.commit()

    call_count = 0

    async def mock_generate(
        task_title: str,
        task_description: str,
        task_status: str,
        subtasks: list[dict[str, str]],
        **kwargs: object,
    ) -> list[SubtaskActionOutput]:
        nonlocal call_count
        call_count += 1
        if task_title == "Task That Fails":
            raise RuntimeError("LLM call failed")
        return _make_actions([s["title"] for s in subtasks])

    mock = AsyncMock(side_effect=mock_generate)

    with patch(
        "app.domains.ai.service.generate_subtask_actions",
        mock,
    ):
        # Should NOT raise despite one task failing
        await generate_board_subtask_actions(
            session,
            board_id=board.id,
            user_id=test_user.id,
        )

    # Both tasks were attempted
    assert mock.call_count == 2

    await session.refresh(subtask_fail)
    await session.refresh(subtask_ok)

    # Failed task's subtask has no actions
    assert subtask_fail.action_label is None

    # Successful task's subtask has actions
    assert subtask_ok.action_label == "AI: Analyze results"


@pytest.mark.asyncio
async def test_generate_board_subtask_actions_skips_tasks_without_subtasks(
    session: AsyncSession,
    test_user: User,  # noqa: F821
) -> None:
    """Tasks without subtasks are skipped (no LLM call made)."""
    goal = Goal(
        user_id=test_user.id,
        title="Test Goal",
        original_input="test",
        status=GoalStatus.ACTIVE.value,
        ai_context={},
    )
    session.add(goal)
    await session.flush()

    board = Board(goal_id=goal.id, title="Test Board")
    session.add(board)
    await session.flush()

    task_with = Task(
        board_id=board.id,
        title="Has Subtasks",
        description="desc",
        status="not_started",
        is_goal_node=False,
    )
    task_without = Task(
        board_id=board.id,
        title="No Subtasks",
        description="desc",
        status="not_started",
        is_goal_node=True,
    )
    session.add_all([task_with, task_without])
    await session.flush()

    subtask = Subtask(task_id=task_with.id, title="Do something", position="a0")
    session.add(subtask)
    await session.commit()

    mock = AsyncMock(return_value=_make_actions(["Do something"]))

    with patch(
        "app.domains.ai.service.generate_subtask_actions",
        mock,
    ):
        await generate_board_subtask_actions(
            session,
            board_id=board.id,
            user_id=test_user.id,
        )

    # Only 1 LLM call — the task without subtasks was skipped
    assert mock.call_count == 1


# ── Integration Tests: API Endpoint Wiring ───────────────


@pytest.mark.asyncio
async def test_create_board_from_template_triggers_inline_actions(
    auth_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: F821
) -> None:
    """POST /templates/:id/create-board triggers inline action generation."""
    template = await _create_template_with_subtasks(session, test_user.id)

    with patch(
        "app.domains.templates.router.generate_board_subtask_actions",
        new_callable=AsyncMock,
    ) as mock_gen:
        resp = await auth_client.post(
            f"/api/templates/{template.id}/create-board",
            json={"title": "My Board"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["board_id"]

        # Inline action generation was called with session + correct kwargs
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args.kwargs
        assert call_kwargs["board_id"] == data["board_id"]
        assert call_kwargs["user_id"] == test_user.id


@pytest.mark.asyncio
async def test_save_generated_with_create_board_triggers_inline_actions(
    auth_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: F821
) -> None:
    """POST /templates/save-generated with create_board=True triggers actions."""
    with patch(
        "app.domains.templates.router.generate_board_subtask_actions",
        new_callable=AsyncMock,
    ) as mock_gen:
        resp = await auth_client.post(
            "/api/templates/save-generated",
            json={
                "title": "Generated Template",
                "create_board": True,
                "tasks": [
                    {
                        "id": "t1",
                        "title": "Step 1",
                        "description": "First step",
                        "is_goal_node": False,
                        "depends_on": [],
                        "subtasks": [{"title": "Sub A"}],
                    },
                    {
                        "id": "t2",
                        "title": "Goal",
                        "description": "The goal",
                        "is_goal_node": True,
                        "depends_on": ["t1"],
                        "subtasks": [{"title": "Sub B"}],
                    },
                ],
            },
        )
        assert resp.status_code == 201

        # Inline action generation was triggered
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args.kwargs
        assert call_kwargs["user_id"] == test_user.id
        assert call_kwargs["board_id"]  # non-empty board_id


@pytest.mark.asyncio
async def test_save_generated_without_create_board_no_actions(
    auth_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: F821
) -> None:
    """POST /templates/save-generated without create_board doesn't trigger actions."""
    with patch(
        "app.domains.templates.router.generate_board_subtask_actions",
        new_callable=AsyncMock,
    ) as mock_gen:
        resp = await auth_client.post(
            "/api/templates/save-generated",
            json={
                "title": "Template Only",
                "create_board": False,
                "tasks": [
                    {
                        "id": "t1",
                        "title": "Only Task",
                        "description": "The goal",
                        "is_goal_node": True,
                        "depends_on": [],
                        "subtasks": [{"title": "Sub A"}],
                    },
                ],
            },
        )
        assert resp.status_code == 201

        # No action generation
        mock_gen.assert_not_called()
