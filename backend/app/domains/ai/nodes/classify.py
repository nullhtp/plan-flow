from __future__ import annotations

from app.domains.ai.llm import get_llm
from app.domains.ai.prompts.classify import (
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT,
)
from app.domains.ai.schemas import ClassificationOutput


async def classify_goal(raw_input: str) -> ClassificationOutput:
    """Classify a goal using the LLM and return structured output."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(ClassificationOutput)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    messages = [
        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": CLASSIFICATION_USER_PROMPT.format(raw_input=raw_input),
        },
    ]

    result = await structured_llm.ainvoke(messages)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    if not isinstance(result, ClassificationOutput):
        msg = f"Expected ClassificationOutput, got {type(result)}"  # pyright: ignore[reportUnknownArgumentType]
        raise TypeError(msg)

    return result
