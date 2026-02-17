"""AI router: task chat endpoint with persistent conversation state."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.domains.auth.deps import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["ai"])


# ── Schemas ──────────────────────────────────────────────


class TaskChatRequest(BaseModel):
    """Request body for the task chat endpoint."""

    message: str = Field(
        min_length=1,
        max_length=4000,
        description="The user's chat message",
    )


class TaskChatResponse(BaseModel):
    """Response from the task chat endpoint."""

    response: str = Field(description="The AI assistant's response")
    thread_id: str = Field(description="The conversation thread ID")


# ── Endpoint ─────────────────────────────────────────────


@router.post("/{task_id}/chat", response_model=TaskChatResponse)
async def task_chat(
    task_id: str,
    body: TaskChatRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskChatResponse:
    """Chat with AI about a specific task.

    Maintains persistent conversation history per task using
    LangGraph's PostgreSQL checkpointer.
    """
    from app.domains.boards.models import Board, Task

    # Load task and verify ownership
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    board = await session.get(Board, task.board_id)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        )

    # Verify the board's goal belongs to the current user
    from app.domains.goals.models import Goal

    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Build task context
    dep_titles = [
        d.dependency_task.title
        for d in task.dependencies
        if d.dependency_task is not None
    ]
    dependent_titles = [
        d.dependent_task.title for d in task.dependents if d.dependent_task is not None
    ]

    task_context = (
        f"task_title: {task.title}\n"
        f"task_description: {task.description}\n"
        f"task_status: {task.status}\n"
        f"dependency_titles: {', '.join(dep_titles) if dep_titles else 'None'}\n"
        f"dependent_titles: "
        f"{', '.join(dependent_titles) if dependent_titles else 'None'}"
    )

    goal_context = (
        f"goal_title: {goal.title or 'Untitled'}\ngoal_input: {goal.original_input}"
    )

    # Retrieve memory context
    memory_context = ""
    if settings.ai_memory_enabled:
        try:
            from app.domains.ai.memory import retrieve_relevant_memories
            from app.domains.ai.prompts.memory import format_memory_block

            query = f"{task.title} {task.description} {goal.original_input}"
            memories = await retrieve_relevant_memories(session, current_user.id, query)
            memory_context = format_memory_block(memories)
        except Exception:
            logger.exception("Memory retrieval for task chat failed")

    # Build and invoke the chat graph
    from app.domains.ai.checkpointer import get_checkpointer
    from app.domains.ai.graphs.chat import (
        build_task_chat_graph,
        get_thread_id,
    )

    checkpointer = get_checkpointer()
    graph = build_task_chat_graph()
    compiled = graph.compile(checkpointer=checkpointer)  # pyright: ignore[reportUnknownMemberType]

    thread_id = get_thread_id(task_id)
    config = {"configurable": {"thread_id": thread_id}}

    result = await compiled.ainvoke(  # pyright: ignore[reportUnknownMemberType]
        {
            "messages": [HumanMessage(content=body.message)],
            "task_id": task_id,
            "task_context": task_context,
            "memory_context": memory_context,
            "goal_context": goal_context,
        },
        config,
    )

    # Extract the last AI message
    messages = result.get("messages", [])  # pyright: ignore[reportUnknownMemberType]
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No response from AI",
        )

    ai_message = messages[-1]
    response_text = (
        str(ai_message.content) if hasattr(ai_message, "content") else str(ai_message)
    )  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]

    return TaskChatResponse(
        response=response_text,
        thread_id=thread_id,
    )
