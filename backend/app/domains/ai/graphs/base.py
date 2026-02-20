"""Shared graph utilities for ReAct agent loops.

``should_continue``, ``execute_tools``, and ``extract_field`` are identical
across task-chat and board-chat graphs.  Centralising them here eliminates
~200 lines of duplication.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 15


def should_continue(state: dict[str, Any]) -> str:
    """Decide whether to execute tools or finish.

    Returns ``'execute_tools'`` if the last message has tool calls,
    otherwise ``'end'``.
    """
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
    """Execute tool calls from the last AI message.

    Runs each tool, collects results as ``ToolMessage`` instances, and
    tracks actions in ``tool_actions`` for the response schema.
    """
    messages: list[AnyMessage] = state.get("messages", [])
    tools = state.get("_tools", [])
    tool_actions: list[dict[str, Any]] = list(state.get("tool_actions", []))
    iteration_count: int = state.get("iteration_count", 0)

    # Build tool lookup
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
            # Tool returns a string or dict; parse accordingly
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


def extract_field(context: str, field: str) -> str:
    """Extract a specific field value from a ``key: value`` context string."""
    for line in context.split("\n"):
        if line.lower().startswith(f"{field}: "):
            return line.split(": ", 1)[1].strip()
    return ""


__all__ = [
    "MAX_TOOL_ITERATIONS",
    "execute_tools",
    "extract_field",
    "should_continue",
]
