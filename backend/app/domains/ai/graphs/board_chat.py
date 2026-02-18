"""Board chat graph: ReAct agent loop with tool binding for board-level chat.

Uses the PostgreSQL checkpointer for persistent conversation threads.
Thread ID convention: board-chat-{board_id}

Graph structure:
  respond -> should_continue? -> execute_tools -> respond (loop)
                              -> END (final response)

Max 10 tool-call iterations per turn to prevent infinite loops.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from langchain_core.messages import (
    AnyMessage,
    SystemMessage,
)
from langgraph.graph import END, StateGraph  # pyright: ignore[reportMissingTypeStubs]
from langgraph.graph.message import (
    add_messages,  # pyright: ignore[reportMissingTypeStubs]
)

from app.domains.ai.graphs.base import (
    execute_tools,
    extract_field,
    should_continue,
)
from app.domains.ai.llm import get_chat_llm
from app.domains.ai.prompts.board_chat import BOARD_CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class BoardChatState(dict):  # pyright: ignore[reportMissingTypeArgument]
    """State for the board chat graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    board_id: str
    board_title: str
    goal_context: str
    memory_context: str
    tool_actions: list[dict[str, Any]]
    iteration_count: int


async def respond(state: dict[str, Any]) -> dict[str, Any]:
    """Respond to the user's message with board context."""
    messages: list[AnyMessage] = state.get("messages", [])
    board_title: str = state.get("board_title", "")
    goal_context: str = state.get("goal_context", "")
    memory_context: str = state.get("memory_context", "")
    tools = state.get("_tools", [])

    system_content = BOARD_CHAT_SYSTEM_PROMPT.format(
        board_title=board_title,
        goal_title=extract_field(goal_context, "goal_title"),
        goal_input=extract_field(goal_context, "goal_input"),
        memory_context=memory_context,
    )

    full_messages: list[AnyMessage] = [SystemMessage(content=system_content)]
    full_messages.extend(messages)

    llm = get_chat_llm()
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm  # pyright: ignore[reportAssignmentType]

    response = await llm_with_tools.ainvoke(full_messages)

    return {"messages": [response]}


def build_board_chat_graph(
    tools: list[Any] | None = None,
) -> StateGraph:  # pyright: ignore[reportMissingTypeArgument]
    """Build the board chat state graph with ReAct agent loop.

    Args:
        tools: LangChain tools to bind to the LLM.

    The checkpointer is attached at invocation time via the config.
    """
    tools = tools or []

    graph: StateGraph = StateGraph(BoardChatState)  # pyright: ignore[reportMissingTypeArgument]

    _tools_list = tools

    async def respond_with_tools(state: dict[str, Any]) -> dict[str, Any]:
        state["_tools"] = _tools_list
        return await respond(state)

    async def execute_tools_with_context(state: dict[str, Any]) -> dict[str, Any]:
        state["_tools"] = _tools_list
        return await execute_tools(state)

    graph.add_node("respond", respond_with_tools)  # pyright: ignore[reportUnknownMemberType]
    graph.add_node("execute_tools", execute_tools_with_context)  # pyright: ignore[reportUnknownMemberType]

    graph.set_entry_point("respond")  # pyright: ignore[reportUnknownMemberType]

    graph.add_conditional_edges(  # pyright: ignore[reportUnknownMemberType]
        "respond",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "end": END,
        },
    )

    graph.add_edge("execute_tools", "respond")  # pyright: ignore[reportUnknownMemberType]

    return graph


def get_board_thread_id(board_id: str) -> str:
    """Generate a consistent thread ID for a board chat session."""
    return f"board-chat-{board_id}"
