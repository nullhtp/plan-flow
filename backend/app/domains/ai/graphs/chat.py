"""Task chat graph: LangGraph state graph for task-level AI conversation.

Uses the PostgreSQL checkpointer for persistent conversation threads.
Thread ID convention: task-chat-{task_id}
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph  # pyright: ignore[reportMissingTypeStubs]
from langgraph.graph.message import (
    add_messages,  # pyright: ignore[reportMissingTypeStubs]
)

from app.core.config import settings
from app.domains.ai.prompts.chat import TASK_CHAT_SYSTEM_PROMPT


class TaskChatState(dict):  # pyright: ignore[reportMissingTypeArgument]
    """State for the task chat graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    task_id: str
    task_context: str
    memory_context: str
    goal_context: str


def _get_llm() -> ChatOpenAI:
    """Create a LangChain chat model for task chat."""
    return ChatOpenAI(
        model=settings.ai_default_model,
        api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        base_url="https://openrouter.ai/api/v1",
        timeout=float(settings.ai_llm_timeout),
    )


async def respond(state: dict[str, Any]) -> dict[str, Any]:
    """Respond to the user's message with task context."""
    messages: list[AnyMessage] = state.get("messages", [])
    task_context: str = state.get("task_context", "")
    memory_context: str = state.get("memory_context", "")
    goal_context: str = state.get("goal_context", "")

    # Build system prompt from the template and context
    system_content = TASK_CHAT_SYSTEM_PROMPT.format(
        **_parse_task_context(task_context),
        memory_context=memory_context,
        goal_title=_extract_field(goal_context, "goal_title"),
        goal_input=_extract_field(goal_context, "goal_input"),
    )

    # Construct message list: system + conversation history
    full_messages: list[AnyMessage] = [SystemMessage(content=system_content)]
    full_messages.extend(messages)

    llm = _get_llm()
    response = await llm.ainvoke(full_messages)

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


def _extract_field(context: str, field: str) -> str:
    """Extract a specific field from a context string."""
    for line in context.split("\n"):
        if line.lower().startswith(f"{field}: "):
            return line.split(": ", 1)[1].strip()
    return ""


def build_task_chat_graph() -> StateGraph:  # pyright: ignore[reportMissingTypeArgument]
    """Build the task chat state graph (without checkpointer).

    The checkpointer is attached at invocation time via the config.
    """
    graph: StateGraph = StateGraph(TaskChatState)  # pyright: ignore[reportMissingTypeArgument]

    graph.add_node("respond", respond)  # pyright: ignore[reportUnknownMemberType]
    graph.set_entry_point("respond")  # pyright: ignore[reportUnknownMemberType]
    graph.add_edge("respond", END)  # pyright: ignore[reportUnknownMemberType]

    return graph


def get_thread_id(task_id: str) -> str:
    """Generate a consistent thread ID for a task chat session."""
    return f"task-chat-{task_id}"
