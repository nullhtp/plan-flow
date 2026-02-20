from __future__ import annotations

from typing import Any

from app.domains.ai.lang_utils import get_language_name
from app.domains.ai.llm import get_llm
from app.domains.ai.prompts.questions import (
    QUESTIONS_USER_PROMPT,
    build_system_prompt,
    format_qa_history,
)
from app.domains.ai.schemas import ClassificationOutput, QuestionsOutput


async def generate_questions(
    raw_input: str,
    classification: ClassificationOutput,
    user_context: str = "",
    memory_context: str = "",
) -> QuestionsOutput:
    """Generate initial questions based on goal classification.

    Returns QuestionsOutput with questions and initial readiness assessment.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language = classification.language
    language_name = get_language_name(language)

    user_content = QUESTIONS_USER_PROMPT.format(
        raw_input=raw_input,
        domain=classification.domain,
        complexity=classification.complexity,
        dimensions=", ".join(classification.dimensions),
        language=language,
        qa_history="",
        user_context=user_context,
        memory_context=memory_context,
    )

    system_content = build_system_prompt(
        language=language,
        language_name=language_name,
        round_num=1,
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, QuestionsOutput):
        msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result


async def generate_follow_up_questions(
    raw_input: str,
    classification: ClassificationOutput,
    rounds: list[dict[str, Any]],
    round_num: int,
    user_context: str = "",
    memory_context: str = "",
) -> QuestionsOutput:
    """Generate follow-up questions based on accumulated Q&A history.

    Args:
        raw_input: Original goal text.
        classification: Goal classification output.
        rounds: List of round dicts with questions, answers, readiness.
        round_num: The round number being generated (next round).
        user_context: Formatted user meta block.
        memory_context: Formatted memory block.

    Returns QuestionsOutput with questions and updated readiness assessment.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    language = classification.language
    language_name = get_language_name(language)

    qa_history = format_qa_history(rounds)

    user_content = QUESTIONS_USER_PROMPT.format(
        raw_input=raw_input,
        domain=classification.domain,
        complexity=classification.complexity,
        dimensions=", ".join(classification.dimensions),
        language=language,
        qa_history=qa_history,
        user_context=user_context,
        memory_context=memory_context,
    )

    system_content = build_system_prompt(
        language=language,
        language_name=language_name,
        round_num=round_num,
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, QuestionsOutput):
        msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result
