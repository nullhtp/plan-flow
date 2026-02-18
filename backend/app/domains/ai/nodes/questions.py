from __future__ import annotations

from typing import Any

from app.domains.ai.lang_utils import get_language_name
from app.domains.ai.llm import get_llm
from app.domains.ai.prompts.questions import (
    FOLLOW_UP_SYSTEM_PROMPT,
    FOLLOW_UP_USER_PROMPT,
    QUESTIONS_SYSTEM_PROMPT,
    QUESTIONS_USER_PROMPT,
)
from app.domains.ai.schemas import ClassificationOutput, QuestionItem, QuestionsOutput


async def generate_questions(
    raw_input: str,
    classification: ClassificationOutput,
    user_context: str = "",
    memory_context: str = "",
) -> list[QuestionItem]:
    """Generate initial questions based on goal classification."""
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
        user_context=user_context,
        memory_context=memory_context,
    )

    system_content = QUESTIONS_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, QuestionsOutput):
        msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result.questions


async def generate_follow_up_questions(
    raw_input: str,
    classification: ClassificationOutput,
    questions: list[QuestionItem],
    answers: dict[str, Any],
    user_context: str = "",
    memory_context: str = "",
) -> list[QuestionItem]:
    """Generate follow-up questions based on initial answers."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    # Format Q&A pairs for the prompt
    qa_lines: list[str] = []
    for q in questions:
        answer = answers.get(q.id, "(not answered)")
        qa_lines.append(f"Q ({q.id}): {q.text}\nA: {answer}")
    qa_pairs = "\n\n".join(qa_lines)

    language = classification.language
    language_name = get_language_name(language)

    user_content = FOLLOW_UP_USER_PROMPT.format(
        raw_input=raw_input,
        domain=classification.domain,
        complexity=classification.complexity,
        language=language,
        qa_pairs=qa_pairs,
        user_context=user_context,
        memory_context=memory_context,
    )

    system_content = FOLLOW_UP_SYSTEM_PROMPT.format(
        language=language,
        language_name=language_name,
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, QuestionsOutput):
        msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result.questions
