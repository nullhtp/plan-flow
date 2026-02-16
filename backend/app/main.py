from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.domains.auth.router import router as auth_router
from app.domains.boards.router import goals_router as boards_goals_router
from app.domains.boards.router import router as boards_router
from app.domains.boards.router import subtasks_router as boards_subtasks_router
from app.domains.boards.router import tasks_router as boards_tasks_router
from app.domains.goals.router import router as goals_router

app = FastAPI(
    title="PlanFlow API",
    description="AI-powered DAG-based task planning",
    version="0.2.0",
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


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
