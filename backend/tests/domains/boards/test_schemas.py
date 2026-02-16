from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.ai.schemas import (
    BoardGenerationColumnOutput,
    BoardGenerationOutput,
    BoardGenerationTaskOutput,
)


def test_board_generation_output_valid() -> None:
    """Valid board generation output parses correctly."""
    data = {
        "board_title": "Relocate to Lisbon",
        "columns": [
            {
                "title": "Research",
                "description": "Gather information",
                "position": 0,
                "tasks": [
                    {
                        "title": "Research visa requirements",
                        "description": "Check Portuguese visa options",
                        "position": 0,
                        "due_date": "2026-03-01",
                        "priority": "high",
                        "estimated_minutes": 60,
                    },
                    {
                        "title": "Research neighborhoods",
                        "description": "Find suitable areas in Lisbon",
                        "position": 1,
                        "due_date": None,
                        "priority": "medium",
                        "estimated_minutes": 90,
                    },
                ],
            },
            {
                "title": "Documentation",
                "description": "Prepare paperwork",
                "position": 1,
                "tasks": [
                    {
                        "title": "Gather documents",
                        "description": "Collect required paperwork",
                        "position": 0,
                        "due_date": None,
                        "priority": None,
                        "estimated_minutes": None,
                    },
                    {
                        "title": "Apply for visa",
                        "description": "Submit visa application",
                        "position": 1,
                        "due_date": "2026-03-15",
                        "priority": "high",
                        "estimated_minutes": 120,
                    },
                ],
            },
            {
                "title": "Logistics",
                "description": "Handle moving logistics",
                "position": 2,
                "tasks": [
                    {
                        "title": "Book flight",
                        "description": "Book one-way flight to Lisbon",
                        "position": 0,
                        "due_date": "2026-04-01",
                        "priority": "high",
                        "estimated_minutes": 30,
                    },
                    {
                        "title": "Arrange pet transport",
                        "description": "Set up cat transport",
                        "position": 1,
                        "due_date": None,
                        "priority": "medium",
                        "estimated_minutes": None,
                    },
                ],
            },
        ],
    }
    result = BoardGenerationOutput.model_validate(data)
    assert result.board_title == "Relocate to Lisbon"
    assert len(result.columns) == 3
    assert result.columns[0].title == "Research"
    assert len(result.columns[0].tasks) == 2
    assert result.columns[0].tasks[0].priority == "high"
    assert result.columns[0].tasks[0].due_date == "2026-03-01"
    # Nullable fields
    assert result.columns[1].tasks[0].priority is None
    assert result.columns[1].tasks[0].estimated_minutes is None


def test_board_generation_output_too_few_columns() -> None:
    """Less than 3 columns fails validation."""
    data = {
        "board_title": "Test",
        "columns": [
            {
                "title": "Col1",
                "description": "D1",
                "position": 0,
                "tasks": [
                    {"title": "T1", "description": "D", "position": 0},
                    {"title": "T2", "description": "D", "position": 1},
                ],
            },
            {
                "title": "Col2",
                "description": "D2",
                "position": 1,
                "tasks": [
                    {"title": "T3", "description": "D", "position": 0},
                    {"title": "T4", "description": "D", "position": 1},
                ],
            },
        ],
    }
    with pytest.raises(ValidationError):
        BoardGenerationOutput.model_validate(data)


def test_board_generation_output_too_few_tasks() -> None:
    """Less than 2 tasks per column fails validation."""
    data = {
        "board_title": "Test",
        "columns": [
            {
                "title": "Col1",
                "description": "D1",
                "position": 0,
                "tasks": [
                    {"title": "T1", "description": "D", "position": 0},
                ],
            },
            {
                "title": "Col2",
                "description": "D2",
                "position": 1,
                "tasks": [
                    {"title": "T2", "description": "D", "position": 0},
                    {"title": "T3", "description": "D", "position": 1},
                ],
            },
            {
                "title": "Col3",
                "description": "D3",
                "position": 2,
                "tasks": [
                    {"title": "T4", "description": "D", "position": 0},
                    {"title": "T5", "description": "D", "position": 1},
                ],
            },
        ],
    }
    with pytest.raises(ValidationError):
        BoardGenerationOutput.model_validate(data)


def test_task_output_nullable_metadata() -> None:
    """Task output accepts null metadata fields."""
    task = BoardGenerationTaskOutput(
        title="Research",
        description="Do research",
        position=0,
        due_date=None,
        priority=None,
        estimated_minutes=None,
    )
    assert task.due_date is None
    assert task.priority is None
    assert task.estimated_minutes is None


def test_column_output_valid() -> None:
    """Column output with nested tasks parses correctly."""
    col = BoardGenerationColumnOutput(
        title="Planning",
        description="Initial planning phase",
        position=0,
        tasks=[
            BoardGenerationTaskOutput(
                title="Define scope",
                description="Define project scope",
                position=0,
            ),
            BoardGenerationTaskOutput(
                title="Set timeline",
                description="Establish timeline",
                position=1,
                priority="high",
            ),
        ],
    )
    assert col.title == "Planning"
    assert len(col.tasks) == 2
