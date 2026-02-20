"""Tool registry: provides context-based tool sets for AI chat interactions.

Each function returns a list of LangChain tools with context (board_id, task_id,
user_id, db_session) pre-injected via closures.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.tools.mutations import (
    make_board_save_artifact,
    make_create_subtask,
    make_delete_subtask,
    make_save_artifact,
    make_toggle_subtask,
    make_update_artifact,
    make_update_task_field,
    make_update_task_status,
)
from app.domains.ai.tools.retrieval import (
    make_get_blocked_tasks,
    make_get_board_overview,
    make_get_board_progress,
    make_get_task_dependencies,
    make_get_task_details,
    make_list_all_tasks,
)
from app.domains.ai.tools.structure import (
    make_add_dependency,
    make_add_task,
    make_remove_dependency,
    make_remove_task,
    make_split_task,
)
from app.domains.ai.tools.web_search import make_web_search

_url_fetch_available = False
try:
    from app.domains.ai.tools.url_fetch import make_fetch_url_content

    _url_fetch_available = True
except ImportError:
    pass


def get_task_chat_tools(
    *,
    db: AsyncSession,
    board_id: str,
    task_id: str,
    user_id: str,
    thread_id: str,
) -> list[Any]:
    """Return the tool set for task-level chat.

    Includes retrieval tools, task mutation tools, artifact tools,
    URL fetch, and optionally web search.
    """
    tools: list[Any] = [
        # Retrieval (read-only, immediate)
        make_get_task_details(db, board_id, user_id),
        make_get_board_overview(db, board_id, user_id),
        make_get_blocked_tasks(db, board_id, user_id),
        make_get_task_dependencies(db, board_id, user_id),
        # Mutations
        make_update_task_field(db, board_id, user_id, thread_id),
        make_update_task_status(db, board_id, user_id, thread_id),
        make_create_subtask(db, board_id, user_id, thread_id),
        make_toggle_subtask(db, board_id, user_id, thread_id),
        make_delete_subtask(db, board_id, user_id, thread_id),
        # Artifacts
        make_save_artifact(db, board_id, task_id, user_id, thread_id),
        make_update_artifact(db, board_id, user_id, thread_id),
    ]

    # Optional URL fetch
    if _url_fetch_available:
        tools.append(make_fetch_url_content())  # pyright: ignore[reportPossiblyUnbound]

    # Optional web search
    ws = make_web_search()
    if ws is not None:
        tools.append(ws)

    return tools


def get_board_chat_tools(
    *,
    db: AsyncSession,
    board_id: str,
    user_id: str,
    thread_id: str,
) -> list[Any]:
    """Return the tool set for board-level chat.

    Includes retrieval tools, task mutation tools, board structure tools,
    artifact tools (with task_id parameter), URL fetch, and optionally
    web search.
    """
    tools: list[Any] = [
        # Retrieval (read-only, immediate)
        make_get_task_details(db, board_id, user_id),
        make_get_board_overview(db, board_id, user_id),
        make_get_blocked_tasks(db, board_id, user_id),
        make_get_task_dependencies(db, board_id, user_id),
        make_list_all_tasks(db, board_id, user_id),
        make_get_board_progress(db, board_id, user_id),
        # Task mutations
        make_update_task_field(db, board_id, user_id, thread_id),
        make_update_task_status(db, board_id, user_id, thread_id),
        make_create_subtask(db, board_id, user_id, thread_id),
        # Board structure mutations (all require confirmation)
        make_add_task(db, board_id, user_id, thread_id),
        make_remove_task(db, board_id, user_id, thread_id),
        make_add_dependency(db, board_id, user_id, thread_id),
        make_remove_dependency(db, board_id, user_id, thread_id),
        make_split_task(db, board_id, user_id, thread_id),
        # Artifacts (board version accepts task_id as parameter)
        make_board_save_artifact(db, board_id, user_id, thread_id),
        make_update_artifact(db, board_id, user_id, thread_id),
    ]

    # Optional URL fetch
    if _url_fetch_available:
        tools.append(make_fetch_url_content())  # pyright: ignore[reportPossiblyUnbound]

    # Optional web search
    ws = make_web_search()
    if ws is not None:
        tools.append(ws)

    return tools
