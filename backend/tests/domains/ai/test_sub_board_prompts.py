"""Unit tests for sub-board question and skeleton prompts.

These tests verify prompt templates are well-formed and contain
expected placeholders without requiring LLM calls.
"""

from __future__ import annotations

from app.domains.ai.prompts.sub_board_questions import (
    SUB_BOARD_QUESTIONS_SYSTEM_PROMPT,
    SUB_BOARD_QUESTIONS_USER_PROMPT,
)

# ── Sub-board question prompts ───────────────────────────


def test_question_system_prompt_contains_id_prefix_instruction() -> None:
    """The system prompt instructs question IDs to be prefixed with 'sbq'."""
    assert "sbq" in SUB_BOARD_QUESTIONS_SYSTEM_PROMPT


def test_question_system_prompt_contains_question_count_range() -> None:
    """The system prompt specifies 2-4 questions."""
    assert "2-4" in SUB_BOARD_QUESTIONS_SYSTEM_PROMPT


def test_question_system_prompt_contains_field_types() -> None:
    """The system prompt mentions all supported field types."""
    for field_type in ("text", "select", "multiselect", "number"):
        assert field_type in SUB_BOARD_QUESTIONS_SYSTEM_PROMPT


def test_question_system_prompt_has_language_placeholder() -> None:
    """The system prompt has language placeholders for i18n."""
    assert "{language}" in SUB_BOARD_QUESTIONS_SYSTEM_PROMPT
    assert "{language_name}" in SUB_BOARD_QUESTIONS_SYSTEM_PROMPT


def test_question_user_prompt_has_task_placeholders() -> None:
    """The user prompt has all required context placeholders."""
    for placeholder in (
        "{task_title}",
        "{task_description}",
        "{board_title}",
        "{goal_context}",
        "{language}",
    ):
        assert placeholder in SUB_BOARD_QUESTIONS_USER_PROMPT


def test_question_user_prompt_renders_without_error() -> None:
    """The user prompt can be formatted with sample values."""
    rendered = SUB_BOARD_QUESTIONS_USER_PROMPT.format(
        task_title="Find housing in Lisbon",
        task_description="Research and secure housing",
        board_title="Relocate to Portugal",
        goal_context="Moving from NYC to Lisbon for remote work",
        language="en",
        user_context="",
        memory_context="",
    )
    assert "Find housing in Lisbon" in rendered
    assert "Relocate to Portugal" in rendered


# ── Sub-board skeleton prompts ───────────────────────────


def test_skeleton_prompts_importable() -> None:
    """Sub-board skeleton prompts can be imported."""
    from app.domains.ai.prompts.generate_board import (
        SUB_BOARD_SKELETON_SYSTEM_PROMPT,
        SUB_BOARD_SKELETON_USER_PROMPT,
    )

    assert "3" in SUB_BOARD_SKELETON_SYSTEM_PROMPT
    assert "15" in SUB_BOARD_SKELETON_SYSTEM_PROMPT
    assert "{task_title}" in SUB_BOARD_SKELETON_USER_PROMPT


def test_skeleton_system_prompt_specifies_task_range() -> None:
    """The skeleton prompt enforces the 3-15 task range."""
    from app.domains.ai.prompts.generate_board import (
        SUB_BOARD_SKELETON_SYSTEM_PROMPT,
    )

    # Should mention both bounds of the range
    assert "3" in SUB_BOARD_SKELETON_SYSTEM_PROMPT
    assert "15" in SUB_BOARD_SKELETON_SYSTEM_PROMPT
