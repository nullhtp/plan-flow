from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.domains.ai.prompts.classify import (
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT,
)
from app.domains.ai.schemas import ClassificationOutput


def get_classification_chain() -> ChatOpenAI:
    """Create a LangChain chat model configured for classification."""
    return ChatOpenAI(
        model=settings.ai_default_model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


async def classify_goal(raw_input: str) -> ClassificationOutput:
    """Classify a goal using the LLM and return structured output."""
    llm = get_classification_chain()
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
