from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.domains.ai.router import (
    actions_router as ai_actions_router,
)
from app.domains.ai.router import (
    boards_chat_router as ai_boards_chat_router,
)
from app.domains.ai.router import router as ai_router
from app.domains.auth.router import router as auth_router
from app.domains.boards.router import goals_router as boards_goals_router
from app.domains.boards.router import router as boards_router
from app.domains.boards.router import subtasks_router as boards_subtasks_router
from app.domains.boards.router import tasks_router as boards_tasks_router
from app.domains.goals.router import router as goals_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    # Startup
    if settings.ai_memory_enabled:
        try:
            from app.domains.ai.checkpointer import init_checkpointer

            await init_checkpointer()
        except Exception:
            logger.exception("Failed to initialize LangGraph checkpointer")

    yield

    # Shutdown
    if settings.ai_memory_enabled:
        try:
            from app.domains.ai.checkpointer import close_checkpointer

            await close_checkpointer()
        except Exception:
            logger.exception("Failed to close LangGraph checkpointer")


app = FastAPI(
    title="PlanFlow API",
    description="AI-powered DAG-based task planning",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(goals_router, prefix="/api")
app.include_router(boards_router, prefix="/api")
app.include_router(boards_tasks_router, prefix="/api")
app.include_router(boards_subtasks_router, prefix="/api")
app.include_router(boards_goals_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(ai_actions_router, prefix="/api")
app.include_router(ai_boards_chat_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
