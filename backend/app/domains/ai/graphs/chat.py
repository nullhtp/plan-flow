"""Task chat graph: ReAct agent loop with tool binding.

Uses the PostgreSQL checkpointer for persistent conversation threads.
Thread ID convention: task-chat-{task_id}

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
from app.domains.ai.prompts.chat import TASK_CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class TaskChatState(dict):  # pyright: ignore[reportMissingTypeArgument]
    """State for the task chat graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    task_id: str
    task_context: str
    memory_context: str
    goal_context: str
    user_context: str
    tool_actions: list[dict[str, Any]]
    iteration_count: int


async def respond(state: dict[str, Any]) -> dict[str, Any]:
    """Respond to the user's message with task context.

    On the first call, prepends the system prompt. The LLM is bound to tools
    so it can decide whether to call them.
    """
    messages: list[AnyMessage] = state.get("messages", [])
    task_context: str = state.get("task_context", "")
    memory_context: str = state.get("memory_context", "")
    goal_context: str = state.get("goal_context", "")
    user_context: str = state.get("user_context", "")
    tools = state.get("_tools", [])

    # Build system prompt from the template and context
    system_content = TASK_CHAT_SYSTEM_PROMPT.format(
        **_parse_task_context(task_context),
        user_context=user_context,
        memory_context=memory_context,
        goal_title=extract_field(goal_context, "goal_title"),
        goal_input=extract_field(goal_context, "goal_input"),
    )

    # Construct message list: system + conversation history
    full_messages: list[AnyMessage] = [SystemMessage(content=system_content)]
    full_messages.extend(messages)

    llm = get_chat_llm()
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm  # pyright: ignore[reportAssignmentType]

    response = await llm_with_tools.ainvoke(full_messages)

    return {"messages": [response]}


def _parse_task_context(task_context: str) -> dict[str, str]:
    """Parse task context string into template variables."""
    # Task context is formatted as key: value lines
    result: dict[str, str] = {
        "task_title": "",
        "task_description": "",
        "task_status": "",
        "dependency_titles": "None",
        "dependent_titles": "None",
    }
    for line in task_context.split("\n"):
        if ": " in line:
            key, _, value = line.partition(": ")
            key_clean = key.strip().lower().replace(" ", "_")
            if key_clean in result:
                result[key_clean] = value.strip()
    return result


def build_task_chat_graph(
    tools: list[Any] | None = None,
) -> StateGraph:  # pyright: ignore[reportMissingTypeArgument]
    """Build the task chat state graph with ReAct agent loop.

    Args:
        tools: LangChain tools to bind to the LLM. Passed through state
               so respond/execute_tools nodes can access them.

    The checkpointer is attached at invocation time via the config.
    """
    tools = tools or []

    graph: StateGraph = StateGraph(TaskChatState)  # pyright: ignore[reportMissingTypeArgument]

    # Inject tools into state via a wrapper
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

    # Conditional edge: check for tool calls
    graph.add_conditional_edges(  # pyright: ignore[reportUnknownMemberType]
        "respond",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "end": END,
        },
    )

    # After tool execution, loop back to respond
    graph.add_edge("execute_tools", "respond")  # pyright: ignore[reportUnknownMemberType]

    return graph


def get_thread_id(task_id: str) -> str:
    """Generate a consistent thread ID for a task chat session."""
    return f"task-chat-{task_id}"
