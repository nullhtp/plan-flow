"""Unit tests for AI board generation schemas (DAG-based)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.ai.schemas import (
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)


def test_board_generation_output_valid() -> None:
    """Valid DAG board generation output parses correctly."""
    data = {
        "board_title": "Relocate to Lisbon",
        "tasks": [
            {
                "id": "t1",
                "title": "Research visa requirements",
                "description": "Check Portuguese visa options",
                "depends_on": [],
                "is_goal_node": False,
                "due_date": "2026-03-01",
                "priority": "high",
                "estimated_minutes": 60,
            },
            {
                "id": "t2",
                "title": "Research neighborhoods",
                "description": "Find suitable areas in Lisbon",
                "depends_on": [],
                "is_goal_node": False,
                "due_date": None,
                "priority": "medium",
                "estimated_minutes": 90,
            },
            {
                "id": "t3",
                "title": "Gather documents",
                "description": "Collect required paperwork",
                "depends_on": ["t1"],
                "is_goal_node": False,
                "due_date": None,
                "priority": None,
                "estimated_minutes": None,
            },
            {
                "id": "t4",
                "title": "Apply for visa",
                "description": "Submit visa application",
                "depends_on": ["t3"],
                "is_goal_node": False,
                "due_date": "2026-03-15",
                "priority": "high",
                "estimated_minutes": 120,
            },
            {
                "id": "t5",
                "title": "Book flight",
                "description": "Book one-way flight to Lisbon",
                "depends_on": ["t4", "t2"],
                "is_goal_node": True,
                "due_date": "2026-04-01",
                "priority": "high",
                "estimated_minutes": 30,
            },
        ],
    }
    result = BoardGenerationOutput.model_validate(data)
    assert result.board_title == "Relocate to Lisbon"
    assert len(result.tasks) == 5
    assert result.tasks[0].id == "t1"
    assert result.tasks[0].priority == "high"
    assert result.tasks[0].due_date == "2026-03-01"
    assert result.tasks[0].depends_on == []
    assert result.tasks[0].is_goal_node is False
    # Goal node
    assert result.tasks[4].is_goal_node is True
    assert result.tasks[4].depends_on == ["t4", "t2"]
    # Nullable fields
    assert result.tasks[2].priority is None
    assert result.tasks[2].estimated_minutes is None


def test_task_output_nullable_metadata() -> None:
    """Task output accepts null metadata fields."""
    task = BoardGenerationTaskOutput(
        id="t1",
        title="Research",
        description="Do research",
        depends_on=[],
        is_goal_node=False,
        due_date=None,
        priority=None,
        estimated_minutes=None,
    )
    assert task.due_date is None
    assert task.priority is None
    assert task.estimated_minutes is None


def test_task_output_defaults() -> None:
    """Task output has sensible defaults for optional fields."""
    task = BoardGenerationTaskOutput(
        id="t1",
        title="Research",
        description="Do research",
    )
    assert task.depends_on == []
    assert task.is_goal_node is False
    assert task.due_date is None
    assert task.priority is None
    assert task.estimated_minutes is None


def test_board_generation_output_missing_title() -> None:
    """Missing board_title fails validation."""
    data = {
        "tasks": [
            {
                "id": "t1",
                "title": "Task",
                "description": "Do thing",
                "is_goal_node": True,
            },
        ],
    }
    with pytest.raises(ValidationError):
        BoardGenerationOutput.model_validate(data)


def test_task_output_missing_required_fields() -> None:
    """Missing required fields (id, title, description) fails validation."""
    with pytest.raises(ValidationError):
        BoardGenerationTaskOutput.model_validate({"title": "No ID or desc"})


def test_board_generation_output_empty_tasks() -> None:
    """Empty tasks list is technically valid at schema level (validation is in dag_utils)."""  # noqa: E501
    data = {
        "board_title": "Test",
        "tasks": [],
    }
    result = BoardGenerationOutput.model_validate(data)
    assert len(result.tasks) == 0
