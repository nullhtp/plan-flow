from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.ai.schemas import ClassificationOutput, QuestionsOutput


def test_classification_output_valid() -> None:
    """Valid classification output parses correctly."""
    data = {
        "domain": "relocation",
        "complexity": 4,
        "confidence": 0.85,
        "dimensions": ["timeline", "budget", "housing"],
        "suggested_title": "Relocate to Lisbon",
        "rejection_reason": None,
        "refinement_suggestions": [],
    }
    result = ClassificationOutput.model_validate(data)
    assert result.domain == "relocation"
    assert result.complexity == 4
    assert result.confidence == 0.85
    assert len(result.dimensions) == 3
    assert result.suggested_title == "Relocate to Lisbon"
    assert result.rejection_reason is None


def test_classification_output_rejection() -> None:
    """Classification with rejection fields parses correctly."""
    data = {
        "domain": "unknown",
        "complexity": 1,
        "confidence": 0.1,
        "dimensions": [],
        "suggested_title": "Be Happier",
        "rejection_reason": "Too vague",
        "refinement_suggestions": [
            "Practice meditation daily for 30 days",
            "Start a gratitude journal",
        ],
    }
    result = ClassificationOutput.model_validate(data)
    assert result.confidence == 0.1
    assert result.rejection_reason == "Too vague"
    assert len(result.refinement_suggestions) == 2


def test_classification_output_invalid_complexity() -> None:
    """Complexity outside 1-5 range fails validation."""
    data = {
        "domain": "test",
        "complexity": 6,
        "confidence": 0.5,
        "dimensions": [],
        "suggested_title": "Test",
    }
    with pytest.raises(ValidationError):
        ClassificationOutput.model_validate(data)


def test_questions_output_valid() -> None:
    """Valid questions output parses correctly."""
    data = {
        "questions": [
            {
                "id": "q1",
                "text": "What is your budget?",
                "type": "select",
                "options": ["Low", "Medium", "High"],
                "rationale": "Budget affects options",
                "required": True,
            },
            {
                "id": "q2",
                "text": "Timeline?",
                "type": "text",
                "options": None,
                "rationale": "Helps set deadlines",
                "required": True,
            },
            {
                "id": "q3",
                "text": "Experience level?",
                "type": "number",
                "options": None,
                "rationale": "Adjusts complexity",
                "required": False,
            },
        ]
    }
    result = QuestionsOutput.model_validate(data)
    assert len(result.questions) == 3
    assert result.questions[0].type == "select"
    assert result.questions[0].options is not None
    assert result.questions[1].options is None


def test_questions_output_too_few() -> None:
    """Less than 3 questions fails validation."""
    data = {
        "questions": [
            {
                "id": "q1",
                "text": "One question",
                "type": "text",
                "rationale": "Only one",
            },
        ]
    }
    with pytest.raises(ValidationError):
        QuestionsOutput.model_validate(data)
