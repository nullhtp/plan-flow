"""Shared LLM factory for the AI domain.

All node modules should use ``get_llm()`` instead of constructing
``ChatOpenAI`` instances directly, ensuring consistent configuration.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_llm() -> ChatOpenAI:
    """Create a LangChain chat model with the project's default settings."""
    return ChatOpenAI(
        model=settings.ai_default_model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


def get_chat_llm() -> ChatOpenAI:
    """Create a LangChain chat model for conversational (chat) endpoints.

    Uses ``ai_chat_model`` if configured, falling back to the default model.
    """
    model = settings.ai_chat_model or settings.ai_default_model
    return ChatOpenAI(
        model=model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


__all__ = ["get_chat_llm", "get_llm"]
