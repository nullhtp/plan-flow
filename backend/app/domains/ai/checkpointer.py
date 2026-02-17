"""LangGraph PostgreSQL checkpointer for persistent conversation state.

Manages the AsyncPostgresSaver lifecycle: initialization on FastAPI startup,
teardown on shutdown. The checkpointer creates its own tables (separate from
Alembic migrations) on first setup.
"""

from __future__ import annotations

import logging
from contextlib import AsyncExitStack

from langgraph.checkpoint.postgres.aio import (
    AsyncPostgresSaver,  # pyright: ignore[reportMissingTypeStubs]
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton — set during FastAPI lifespan
_checkpointer: AsyncPostgresSaver | None = None
_exit_stack: AsyncExitStack | None = None


def _get_sync_database_url() -> str:
    """Convert the asyncpg database URL to a psycopg-compatible URL.

    LangGraph's PostgresSaver uses psycopg (sync/async), not asyncpg.
    """
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def init_checkpointer() -> None:
    """Initialize the LangGraph checkpointer and create its tables.

    Should be called during FastAPI startup.
    ``from_conn_string`` returns an async context manager, so we use
    an AsyncExitStack to enter it and keep the connection alive until
    shutdown.
    """
    global _checkpointer, _exit_stack

    conn_string = _get_sync_database_url()

    _exit_stack = AsyncExitStack()
    _checkpointer = await _exit_stack.enter_async_context(
        AsyncPostgresSaver.from_conn_string(conn_string)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    )
    await _checkpointer.setup()  # pyright: ignore[reportUnknownMemberType]
    logger.info("LangGraph checkpointer initialized")


async def close_checkpointer() -> None:
    """Close the checkpointer connection pool.

    Should be called during FastAPI shutdown.
    """
    global _checkpointer, _exit_stack

    if _exit_stack is not None:
        try:
            await _exit_stack.aclose()
        except Exception:
            logger.exception("Error closing checkpointer connection")
        _exit_stack = None
    _checkpointer = None
    logger.info("LangGraph checkpointer closed")


def get_checkpointer() -> AsyncPostgresSaver:
    """Return the initialized checkpointer instance.

    Raises RuntimeError if called before init_checkpointer().
    """
    if _checkpointer is None:
        msg = "Checkpointer not initialized. Ensure init_checkpointer() is called during startup."  # noqa: E501
        raise RuntimeError(msg)
    return _checkpointer
