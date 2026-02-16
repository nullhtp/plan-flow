from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.domains.ai.prompts.questions import (
    FOLLOW_UP_SYSTEM_PROMPT,
    FOLLOW_UP_USER_PROMPT,
    QUESTIONS_SYSTEM_PROMPT,
    QUESTIONS_USER_PROMPT,
)
from app.domains.ai.schemas import ClassificationOutput, QuestionItem, QuestionsOutput


def _get_llm() -> ChatOpenAI:
    """Create a LangChain chat model configured for question generation."""
    return ChatOpenAI(
        model=settings.ai_default_model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


async def generate_questions(
    raw_input: str,
    classification: ClassificationOutput,
) -> list[QuestionItem]:
    """Generate initial questions based on goal classification."""
    llm = _get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    user_content = QUESTIONS_USER_PROMPT.format(
        raw_input=raw_input,
        domain=classification.domain,
        complexity=classification.complexity,
        dimensions=", ".join(classification.dimensions),
    )

    messages = [
        {"role": "system", "content": QUESTIONS_SYSTEM_PROMPT},
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
) -> list[QuestionItem]:
    """Generate follow-up questions based on initial answers."""
    llm = _get_llm()
    structured_llm = llm.with_structured_output(QuestionsOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    # Format Q&A pairs for the prompt
    qa_lines: list[str] = []
    for q in questions:
        answer = answers.get(q.id, "(not answered)")
        qa_lines.append(f"Q ({q.id}): {q.text}\nA: {answer}")
    qa_pairs = "\n\n".join(qa_lines)

    user_content = FOLLOW_UP_USER_PROMPT.format(
        raw_input=raw_input,
        domain=classification.domain,
        complexity=classification.complexity,
        qa_pairs=qa_pairs,
    )

    messages = [
        {"role": "system", "content": FOLLOW_UP_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, QuestionsOutput):
        msg = f"Expected QuestionsOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result.questions
