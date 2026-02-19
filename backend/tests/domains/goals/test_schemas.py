from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domains.ai.schemas import ClassificationOutput, QuestionItem, QuestionsOutput
from app.domains.goals.schemas import QuestionSchema


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
    """Valid questions output with options on all types parses correctly."""
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
                "options": ["1-2 months", "3-4 months", "5-6 months"],
                "rationale": "Helps set deadlines",
                "required": True,
            },
            {
                "id": "q3",
                "text": "Experience level?",
                "type": "number",
                "options": ["1-3 years", "4-6 years", "7+ years"],
                "rationale": "Adjusts complexity",
                "required": False,
            },
        ]
    }
    result = QuestionsOutput.model_validate(data)
    assert len(result.questions) == 3
    assert result.questions[0].type == "select"
    assert result.questions[0].options == ["Low", "Medium", "High"]
    assert result.questions[1].options == ["1-2 months", "3-4 months", "5-6 months"]
    assert result.questions[2].options == ["1-3 years", "4-6 years", "7+ years"]


def test_questions_output_too_few() -> None:
    """Less than 3 questions fails validation."""
    data = {
        "questions": [
            {
                "id": "q1",
                "text": "One question",
                "type": "text",
                "options": ["A", "B", "C"],
                "rationale": "Only one",
            },
        ]
    }
    with pytest.raises(ValidationError):
        QuestionsOutput.model_validate(data)


# --- New tests for options-always-required behavior ---


def test_question_schema_options_required() -> None:
    """QuestionSchema requires non-null options with at least 3 items."""
    # Valid: 3 options
    q = QuestionSchema(
        id="q1",
        text="Test?",
        type="text",
        options=["A", "B", "C"],
        rationale="test",
    )
    assert q.options == ["A", "B", "C"]
    assert q.allow_other is True


def test_question_schema_null_options_rejected() -> None:
    """QuestionSchema rejects null options."""
    with pytest.raises(ValidationError):
        QuestionSchema(
            id="q1",
            text="Test?",
            type="text",
            options=None,  # type: ignore[arg-type]
            rationale="test",
        )


def test_question_schema_empty_options_rejected() -> None:
    """QuestionSchema rejects empty options list."""
    with pytest.raises(ValidationError):
        QuestionSchema(
            id="q1",
            text="Test?",
            type="text",
            options=[],
            rationale="test",
        )


def test_question_schema_too_few_options_rejected() -> None:
    """QuestionSchema rejects options with fewer than 3 items."""
    with pytest.raises(ValidationError):
        QuestionSchema(
            id="q1",
            text="Test?",
            type="select",
            options=["A", "B"],
            rationale="test",
        )


def test_question_schema_too_many_options_rejected() -> None:
    """QuestionSchema rejects options with more than 6 items."""
    with pytest.raises(ValidationError):
        QuestionSchema(
            id="q1",
            text="Test?",
            type="select",
            options=["A", "B", "C", "D", "E", "F", "G"],
            rationale="test",
        )


def test_question_schema_allow_other_defaults_true() -> None:
    """QuestionSchema.allow_other defaults to True."""
    q = QuestionSchema(
        id="q1",
        text="Test?",
        type="select",
        options=["A", "B", "C"],
        rationale="test",
    )
    assert q.allow_other is True


def test_question_schema_allow_other_false() -> None:
    """QuestionSchema.allow_other can be set to False."""
    q = QuestionSchema(
        id="q1",
        text="Test?",
        type="select",
        options=["A", "B", "C"],
        rationale="test",
        allow_other=False,
    )
    assert q.allow_other is False


def test_question_item_mirrors_schema() -> None:
    """QuestionItem (AI-side) has the same validation as QuestionSchema."""
    # Valid
    qi = QuestionItem(
        id="q1",
        text="Test?",
        type="text",
        options=["A", "B", "C"],
        rationale="test",
    )
    assert qi.options == ["A", "B", "C"]
    assert qi.allow_other is True

    # Null options rejected
    with pytest.raises(ValidationError):
        QuestionItem(
            id="q1",
            text="Test?",
            type="text",
            options=None,  # type: ignore[arg-type]
            rationale="test",
        )

    # Too few options rejected
    with pytest.raises(ValidationError):
        QuestionItem(
            id="q1",
            text="Test?",
            type="text",
            options=["A"],
            rationale="test",
        )
