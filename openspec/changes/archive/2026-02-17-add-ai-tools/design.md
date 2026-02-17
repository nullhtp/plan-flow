## Context

PlanFlow's AI currently operates in a generate-only mode: it produces structured output (classification, questions, board skeletons, enrichments) and plain-text chat responses, but it cannot take actions. The task chat graph (`graphs/chat.py`) is a single `respond` node with no tool binding. There is no board-level chat at all.

This change introduces LangChain tool use across two interaction points (task chat and board chat), adds a new external dependency (Tavily for web search), and introduces a confirmation flow for destructive actions. This is a cross-cutting change that touches the AI domain's graph definitions, the boards domain's service layer, and introduces a new `pending_action` data model.

### Stakeholders
- End users: gain an AI that can actually help execute their plans, not just advise
- AI domain: new tool definitions, graph rewrites, prompt updates
- Boards domain: new service functions called by tools, new API endpoints

## Goals / Non-Goals

### Goals
- AI autonomously decides when to use tools based on conversation context
- Context-based tool availability: task chat gets task-scoped tools, board chat gets board-wide tools
- Hybrid autonomy: read-only tools execute immediately; mutations to status, task creation/deletion, dependency changes, and subtask deletion require user confirmation
- Web search via Tavily for task research
- Inline tool result display in chat responses (structured action results alongside natural language)
- Persistent conversation threads for both task and board chat (via existing PostgreSQL checkpointer)

### Non-Goals
- Frontend chat UI (separate proposal — backend endpoints only)
- Autonomous/proactive AI actions (no background suggestions without user prompting)
- Tool use during board generation pipeline (generation works well with structured output)
- Multi-turn tool confirmation (one pending action at a time per thread)
- Real-time collaboration (single-user MVP)

## Decisions

### Decision 1: LangChain `@tool` decorator + `bind_tools` for tool definitions

Tools are defined as Python functions decorated with `@tool` from `langchain_core.tools`. Each tool gets a docstring that serves as the tool description for the LLM. The LLM model is bound to tools via `model.bind_tools(tools)`. LangGraph's `ToolNode` handles automatic tool execution.

**Alternatives considered:**
- Raw function-calling JSON schemas: more boilerplate, no automatic execution
- Custom tool protocol: unnecessary when LangChain provides a mature solution
- OpenAI Assistants API tools: locks us to OpenAI, doesn't work through OpenRouter

### Decision 2: ReAct agent pattern for chat graphs

Both task chat and board chat graphs are upgraded to ReAct agent loops: the LLM decides whether to call a tool or respond, tools execute, results feed back to the LLM, and it decides again. This replaces the current single-node `respond` pattern.

LangGraph's `create_react_agent` or a manual `StateGraph` with a conditional edge (tool call vs. final response) implements this. The manual approach is preferred for control over the confirmation flow.

**Graph structure:**
```
respond -> should_continue? -> tool_execute -> respond (loop)
                            -> END (final response)
```

With confirmation, tool_execute checks if the tool requires confirmation. If yes, it stores a `PendingAction` and returns a "confirmation needed" message instead of executing.

### Decision 3: Context-based tool sets

Each interaction point declares its tool set:

| Context | Tools Available |
|---------|----------------|
| Task chat | get_task_details, get_board_overview, get_blocked_tasks, get_task_dependencies, update_task_field, update_task_status, create_subtask, toggle_subtask, delete_subtask, web_search |
| Board chat | get_board_overview, get_task_details, get_blocked_tasks, get_board_progress, list_all_tasks, add_task, remove_task, add_dependency, remove_dependency, split_task, update_task_field, update_task_status, create_subtask, web_search |

Task chat tools are scoped to the task's board context but can read any task on the board. Board chat tools can operate on any task.

### Decision 4: Hybrid autonomy with PendingAction model

A `pending_action` table stores proposed mutations awaiting confirmation:

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | FK(user) | Owner |
| thread_id | string | Chat thread that proposed this action |
| tool_name | string | Which tool was called |
| tool_args | JSON | Arguments the AI passed |
| description | string | Human-readable description of the action |
| status | enum | `pending` / `confirmed` / `rejected` / `expired` |
| created_at | datetime | When proposed |
| expires_at | datetime | Auto-expire after 10 minutes |

**Tools requiring confirmation:**
- `update_task_status` (status changes)
- `add_task`, `remove_task` (structural changes)
- `add_dependency`, `remove_dependency` (dependency changes)
- `delete_subtask` (subtask deletion)
- `split_task` (structural change)

**Tools executing immediately:**
- All `get_*` tools (read-only)
- `update_task_field` (non-status field edits like title, description, priority)
- `create_subtask` (additive, non-destructive)
- `toggle_subtask` (toggling completion)
- `web_search` (read-only external)

### Decision 5: Tavily for web search

Tavily Search API (`tavily-python`) is purpose-built for LLM tool use. It returns structured results (title, URL, content snippet, relevance score) that the AI can synthesize. Configuration via `TAVILY_API_KEY` environment variable. The tool is optional — if the API key is not configured, the web_search tool is not registered.

**Alternatives considered:**
- SerpAPI: more expensive, returns raw Google results that need parsing
- DuckDuckGo: free but unreliable rate limits, limited result quality
- LLM built-in search: not consistently available across OpenRouter models

### Decision 6: Tool results as structured data in chat response

The chat response schema is extended to include tool actions:

```python
class ToolAction(BaseModel):
    tool_name: str
    description: str  # human-readable
    status: str  # "executed", "pending_confirmation", "failed"
    result: dict | None  # tool-specific result data

class ChatResponse(BaseModel):
    response: str  # AI's natural language response
    thread_id: str
    actions: list[ToolAction]  # tools used in this turn
    pending_action_id: str | None  # if confirmation needed
```

This allows the frontend to render inline action cards alongside the chat text.

### Decision 7: Board chat as a new LangGraph graph with dedicated endpoint

A new `POST /api/boards/{board_id}/chat` endpoint with a new `BoardChatGraph` in `graphs/board_chat.py`. Thread ID convention: `board-chat-{board_id}`. This keeps board-level and task-level contexts cleanly separated.

## Risks / Trade-offs

### Risk: LLM tool call reliability
OpenRouter models may not all support tool calling consistently.
- **Mitigation:** The default model (`openai/gpt-5.2`) has excellent tool calling support. Add a `AI_CHAT_MODEL` config separate from `AI_DEFAULT_MODEL` so chat can use a tool-calling-optimized model. Add graceful fallback: if tool call parsing fails, return the raw text response without tool execution.

### Risk: Confirmation flow adds latency and complexity
Users must confirm actions, which breaks the chat flow.
- **Mitigation:** Keep the pending action inline in the chat response. Frontend can render a confirm/reject button right in the message. Auto-expire after 10 minutes. Only one pending action per thread at a time.

### Risk: Tool execution errors during chat
Tools that mutate the database could fail (race conditions, validation errors).
- **Mitigation:** Each tool wraps its execution in try/except and returns structured error results. The AI sees the error and can explain it to the user. Database operations use transactions.

### Risk: Tavily API cost
Each web search costs money.
- **Mitigation:** Optional dependency (skip if no API key). Rate limit: max 3 web searches per chat session. The AI's system prompt instructs it to use web search only when the user explicitly asks for research help or when it genuinely needs external information.

## Migration Plan

1. Add `pending_action` table via Alembic migration
2. Implement tool definitions (no graph changes yet) — unit testable in isolation
3. Upgrade task chat graph to ReAct agent with tool binding
4. Implement confirmation flow (PendingAction CRUD + confirm/reject endpoints)
5. Implement board chat graph + endpoint
6. Add Tavily integration (optional)
7. Update chat response schema with tool action results

All changes are additive. Existing task chat endpoint signature changes (response schema gains new fields) but remains backward-compatible (new fields are optional/default-empty). No existing data is affected.

## Open Questions

1. Should there be a rate limit on tool calls per chat turn (e.g., max 5 tool calls per response)?
2. Should the AI be able to chain confirmable actions (propose multiple mutations at once) or strictly one at a time?
3. Should web search results be cached to avoid duplicate searches for the same query?
