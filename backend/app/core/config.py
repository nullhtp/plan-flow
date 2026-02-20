from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/planflow"
    test_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/planflow_test"
    )

    # Application
    app_name: str = "PlanFlow"
    debug: bool = False

    # Auth / JWT
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Cookies
    cookie_secure: bool = False  # Set True in production (HTTPS)

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # AI / OpenRouter
    openrouter_api_key: str = ""
    ai_default_model: str = "openai/gpt-5.2"
    ai_confidence_threshold: float = 0.3
    ai_llm_timeout: int = 20  # seconds
    ai_max_retries: int = 3
    ai_enrichment_concurrency: int = 5  # max concurrent enrichment LLM calls

    # AI Memory
    ai_memory_enabled: bool = True
    ai_embedding_model: str = "openai/text-embedding-3-small"
    ai_embedding_dimensions: int = 1536
    ai_memory_retrieval_limit: int = 15
    ai_memory_similarity_threshold: float = 0.95
    ai_memory_decay_days: int = 90
    ai_memory_max_per_user: int = 500

    # AI Chat & Tools
    ai_chat_model: str = ""  # defaults to ai_default_model when empty
    ai_action_suggest_model: str = ""  # fallback: ai_chat_model -> ai_default_model
    perplexity_api_key: str = ""  # Perplexity API key; empty = web search disabled
    perplexity_model: str = "sonar"  # Perplexity Sonar model for web search
    ai_web_search_max_results: int = 5

    # AI Research (generation pipeline)
    ai_max_research_queries: int = 15  # hard ceiling per board generation
    ai_max_fetch_urls: int = 5  # max URLs to fetch full content from
    ai_research_context_max_chars: int = 8000  # max chars for research block in prompts


settings = Settings()
