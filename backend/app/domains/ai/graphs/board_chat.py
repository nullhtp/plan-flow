"""Board chat graph: ReAct agent loop with tool binding for board-level chat.

Uses the PostgreSQL checkpointer for persistent conversation threads.
Thread ID convention: board-chat-{board_id}

Graph structure:
  respond -> should_continue? -> execute_tools -> respond (loop)
                              -> END (final response)

Max 10 tool-call iterations per turn to prevent infinite loops.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph  # pyright: ignore[reportMissingTypeStubs]
from langgraph.graph.message import (
    add_messages,  # pyright: ignore[reportMissingTypeStubs]
)

from app.core.config import settings
from app.domains.ai.prompts.board_chat import BOARD_CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10


class BoardChatState(dict):  # pyright: ignore[reportMissingTypeArgument]
    """State for the board chat graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    board_id: str
    board_title: str
    goal_context: str
    memory_context: str
    tool_actions: list[dict[str, Any]]
    iteration_count: int


def _get_llm() -> ChatOpenAI:
    """Create a LangChain chat model for board chat."""
    model = settings.ai_chat_model or settings.ai_default_model
    return ChatOpenAI(
        model=model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


def _extract_field(context: str, field: str) -> str:
    """Extract a specific field from a context string."""
    for line in context.split("\n"):
        if line.lower().startswith(f"{field}: "):
            return line.split(": ", 1)[1].strip()
    return ""


async def respond(state: dict[str, Any]) -> dict[str, Any]:
    """Respond to the user's message with board context."""
    messages: list[AnyMessage] = state.get("messages", [])
    board_title: str = state.get("board_title", "")
    goal_context: str = state.get("goal_context", "")
    memory_context: str = state.get("memory_context", "")
    tools = state.get("_tools", [])

    system_content = BOARD_CHAT_SYSTEM_PROMPT.format(
        board_title=board_title,
        goal_title=_extract_field(goal_context, "goal_title"),
        goal_input=_extract_field(goal_context, "goal_input"),
        memory_context=memory_context,
    )

    full_messages: list[AnyMessage] = [SystemMessage(content=system_content)]
    full_messages.extend(messages)

    llm = _get_llm()
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm  # pyright: ignore[reportAssignmentType]

    response = await llm_with_tools.ainvoke(full_messages)

    return {"messages": [response]}


def should_continue(state: dict[str, Any]) -> str:
    """Decide whether to execute tools or finish."""
    messages: list[AnyMessage] = state.get("messages", [])
    iteration_count: int = state.get("iteration_count", 0)

    if iteration_count >= MAX_TOOL_ITERATIONS:
        logger.warning(
            "Max tool iterations reached (%d), stopping", MAX_TOOL_ITERATIONS
        )
        return "end"

    if not messages:
        return "end"

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "execute_tools"

    return "end"


async def execute_tools(state: dict[str, Any]) -> dict[str, Any]:
    """Execute tool calls from the last AI message."""
    messages: list[AnyMessage] = state.get("messages", [])
    tools = state.get("_tools", [])
    tool_actions: list[dict[str, Any]] = list(state.get("tool_actions", []))
    iteration_count: int = state.get("iteration_count", 0)

    tool_map: dict[str, Any] = {t.name: t for t in tools}

    last_message = messages[-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}

    new_messages: list[ToolMessage] = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        tool_fn = tool_map.get(tool_name)
        if tool_fn is None:
            result = {"status": "failed", "error": f"Unknown tool: {tool_name}"}
            new_messages.append(
                ToolMessage(content=json.dumps(result), tool_call_id=tool_id)
            )
            tool_actions.append(
                {
                    "tool_name": tool_name,
                    "description": f"Unknown tool: {tool_name}",
                    "status": "failed",
                    "result": result,
                }
            )
            continue

        try:
            result = await tool_fn.ainvoke(tool_args)
            if isinstance(result, str):
                try:
                    result_dict = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    result_dict = {"result": result}
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"result": str(result)}

            new_messages.append(
                ToolMessage(
                    content=json.dumps(result_dict)
                    if isinstance(result_dict, dict)
                    else str(result_dict),
                    tool_call_id=tool_id,
                )
            )

            action_status = result_dict.get("status", "executed")
            tool_actions.append(
                {
                    "tool_name": tool_name,
                    "description": result_dict.get(
                        "description", f"Called {tool_name}"
                    ),
                    "status": action_status,
                    "result": result_dict,
                    "pending_action_id": result_dict.get("pending_action_id"),
                }
            )
        except Exception as e:
            logger.exception("Tool execution error for %s", tool_name)
            error_result = {"status": "failed", "error": str(e)}
            new_messages.append(
                ToolMessage(
                    content=json.dumps(error_result),
                    tool_call_id=tool_id,
                )
            )
            tool_actions.append(
                {
                    "tool_name": tool_name,
                    "description": f"Error executing {tool_name}: {e}",
                    "status": "failed",
                    "result": error_result,
                }
            )

    return {
        "messages": new_messages,
        "tool_actions": tool_actions,
        "iteration_count": iteration_count + 1,
    }


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
