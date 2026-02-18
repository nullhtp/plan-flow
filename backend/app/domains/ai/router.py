"""AI router: task/board chat endpoints and action confirmation endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.domains.ai.schemas import (
    ActionConfirmResponse,
    ActionSuggestionsResponse,
    BoardChatRequest,
    ChatResponse,
    TaskChatRequest,
    ToolAction,
)
from app.domains.auth.deps import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["ai"])
actions_router = APIRouter(prefix="/actions", tags=["ai-actions"])
boards_chat_router = APIRouter(prefix="/boards", tags=["ai"])


# ── Helpers ──────────────────────────────────────────────


async def _validate_board_ownership(
    session: AsyncSession, board_id: str, user_id: str
) -> tuple:  # pyright: ignore[reportMissingTypeArgument]
    """Load board + goal and verify ownership. Returns (board, goal).

    NOTE: This is a router-level helper that raises HTTPException directly.
    It is NOT the same as boards.ownership.validate_board_ownership which
    raises domain errors. Kept here because it returns (board, goal) tuple
    needed by the chat endpoints.
    """
    from app.domains.boards.models import Board
    from app.domains.goals.models import Goal

    board = await session.get(Board, board_id)
    if board is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board not found",
        )

    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return board, goal


def _extract_tool_actions(result: dict) -> tuple[list[ToolAction], str | None]:  # pyright: ignore[reportMissingTypeArgument]
    """Extract ToolAction list and pending_action_id from graph result."""
    tool_actions: list[ToolAction] = []
    pending_action_id: str | None = None

    raw_actions = result.get("tool_actions", [])  # pyright: ignore[reportUnknownMemberType]
    for a in raw_actions:  # pyright: ignore[reportUnknownVariableType]
        action = ToolAction(
            tool_name=a.get("tool_name", "unknown"),  # pyright: ignore[reportUnknownMemberType]
            description=a.get("description", ""),  # pyright: ignore[reportUnknownMemberType]
            status=a.get("status", "unknown"),  # pyright: ignore[reportUnknownMemberType]
            result=a.get("result"),  # pyright: ignore[reportUnknownMemberType]
        )
        tool_actions.append(action)
        if action.status == "pending_confirmation":
            pending_action_id = a.get("pending_action_id")  # pyright: ignore[reportUnknownMemberType]

    return tool_actions, pending_action_id


# ── Action Suggestions Endpoint ─────────────────────────


@router.post(
    "/{task_id}/actions/suggest",
    response_model=ActionSuggestionsResponse,
)
async def suggest_task_actions(
    task_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActionSuggestionsResponse:
    """Generate 2-4 contextual AI action suggestions for a task."""
    # Load task with all relationships eagerly loaded
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import selectinload

    from app.domains.ai.service import generate_action_suggestions
    from app.domains.boards.models import Task, TaskDependency

    stmt = (
        sa_select(Task)
        .where(Task.id == task_id)  # pyright: ignore[reportArgumentType]
        .options(
            selectinload(Task.subtasks),  # pyright: ignore[reportArgumentType]
            selectinload(Task.dependencies).selectinload(
                TaskDependency.dependency_task
            ),  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
            selectinload(Task.dependents).selectinload(TaskDependency.dependent_task),  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
        )
    )
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    await _validate_board_ownership(session, task.board_id, current_user.id)

    # Build subtask summary
    subtask_lines: list[str] = []
    for st in task.subtasks:
        done_marker = "[x]" if st.completed else "[ ]"
        subtask_lines.append(f"- {done_marker} {st.title}")
    subtasks_text = "\n".join(subtask_lines) if subtask_lines else "None"

    # Build dependency / dependent titles
    dep_titles = [
        d.dependency_task.title
        for d in task.dependencies
        if d.dependency_task is not None
    ]
    dependent_titles = [
        d.dependent_task.title for d in task.dependents if d.dependent_task is not None
    ]

    try:
        result = await generate_action_suggestions(
            task_title=task.title,
            task_description=task.description or "",
            task_status=task.status,
            subtasks=subtasks_text,
            dependency_titles=", ".join(dep_titles) if dep_titles else "None",
            dependent_titles=(
                ", ".join(dependent_titles) if dependent_titles else "None"
            ),
        )
    except Exception:
        logger.exception("Action suggestion generation failed for task %s", task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate action suggestions",
        ) from None

    return result


# ── Task Chat Endpoint ──────────────────────────────────


@router.post("/{task_id}/chat", response_model=ChatResponse)
async def task_chat(
    task_id: str,
    body: TaskChatRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatResponse:
    """Chat with AI about a specific task.

    The AI can use tools to read board state, mutate tasks (with confirmation
    for destructive actions), and search the web. Returns tool action results
    alongside the natural-language response.
    """
    from app.domains.boards.models import Task

    # Load task and verify ownership
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    _board, goal = await _validate_board_ownership(
        session, task.board_id, current_user.id
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
    from app.domains.ai.tools.registry import get_task_chat_tools

    thread_id = get_thread_id(task_id)
    tools = get_task_chat_tools(
        db=session,
        board_id=task.board_id,
        task_id=task_id,
        user_id=current_user.id,
        thread_id=thread_id,
    )

    checkpointer = get_checkpointer()
    graph = build_task_chat_graph(tools=tools)
    compiled = graph.compile(checkpointer=checkpointer)  # pyright: ignore[reportUnknownMemberType]

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

    tool_actions, pending_action_id = _extract_tool_actions(result)

    return ChatResponse(
        response=response_text,
        thread_id=thread_id,
        actions=tool_actions,
        pending_action_id=pending_action_id,
    )


# ── Board Chat Endpoint ─────────────────────────────────


@boards_chat_router.post("/{board_id}/chat", response_model=ChatResponse)
async def board_chat(
    board_id: str,
    body: BoardChatRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatResponse:
    """Chat with AI about a board.

    The AI has access to board-wide tools including structural operations
    (add/remove tasks, manage dependencies, split tasks).
    """
    board, goal = await _validate_board_ownership(session, board_id, current_user.id)

    goal_context = (
        f"goal_title: {goal.title or 'Untitled'}\ngoal_input: {goal.original_input}"
    )

    # Retrieve memory context
    memory_context = ""
    if settings.ai_memory_enabled:
        try:
            from app.domains.ai.memory import retrieve_relevant_memories
            from app.domains.ai.prompts.memory import format_memory_block

            query = f"{board.title} {goal.original_input}"
            memories = await retrieve_relevant_memories(session, current_user.id, query)
            memory_context = format_memory_block(memories)
        except Exception:
            logger.exception("Memory retrieval for board chat failed")

    # Build and invoke the board chat graph
    from app.domains.ai.checkpointer import get_checkpointer
    from app.domains.ai.graphs.board_chat import (
        build_board_chat_graph,
        get_board_thread_id,
    )
    from app.domains.ai.tools.registry import get_board_chat_tools

    thread_id = get_board_thread_id(board_id)
    tools = get_board_chat_tools(
        db=session,
        board_id=board_id,
        user_id=current_user.id,
        thread_id=thread_id,
    )

    checkpointer = get_checkpointer()
    graph = build_board_chat_graph(tools=tools)
    compiled = graph.compile(checkpointer=checkpointer)  # pyright: ignore[reportUnknownMemberType]

    config = {"configurable": {"thread_id": thread_id}}

    result = await compiled.ainvoke(  # pyright: ignore[reportUnknownMemberType]
        {
            "messages": [HumanMessage(content=body.message)],
            "board_id": board_id,
            "board_title": board.title,
            "goal_context": goal_context,
            "memory_context": memory_context,
        },
        config,
    )

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

    tool_actions, pending_action_id = _extract_tool_actions(result)

    return ChatResponse(
        response=response_text,
        thread_id=thread_id,
        actions=tool_actions,
        pending_action_id=pending_action_id,
    )


# ── Action Confirm/Reject Endpoints ─────────────────────


@actions_router.post("/{action_id}/confirm", response_model=ActionConfirmResponse)
async def confirm_pending_action(
    action_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActionConfirmResponse:
    """Confirm a pending AI tool action and execute it."""
    from app.domains.ai.pending_actions import confirm_action

    result = await confirm_action(session, action_id, current_user.id)

    if result["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    return ActionConfirmResponse(
        status=result["status"],
        description=result.get("description"),
        error=result.get("error"),
        result=result.get("result"),
    )


@actions_router.post("/{action_id}/reject", response_model=ActionConfirmResponse)
async def reject_pending_action(
    action_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ActionConfirmResponse:
    """Reject a pending AI tool action."""
    from app.domains.ai.pending_actions import reject_action

    result = await reject_action(session, action_id, current_user.id)

    if result["status"] == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    return ActionConfirmResponse(
        status=result["status"],
        description=result.get("description"),
        error=result.get("error"),
    )
