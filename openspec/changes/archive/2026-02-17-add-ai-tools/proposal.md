# Change: Add AI Tool Use for Chat and Generation Steps

## Why
The AI in PlanFlow currently operates in a purely generative mode — it produces text and structured output but cannot take actions. During task chat, the AI cannot update the task it's discussing, check what's blocked, or help users research information. This limits the AI from being a true execution partner. Adding tool use transforms the AI from a passive advisor into an active collaborator that can read board state, mutate tasks (with user confirmation for destructive actions), search the web, and restructure the board — all driven by the AI's own judgment of what's needed in context.

## What Changes

### New Capability: AI Tools (`ai-tools`)
- **Tool registry** — a context-based system where each AI interaction point (task chat, board chat) declares which tools are available
- **Task mutation tools** — update task status, edit title/description, set priority/due date/estimate, toggle subtask completion, create subtasks
- **Board structure tools** — add tasks, remove tasks, add/remove dependency edges, split a task into multiple tasks
- **Information retrieval tools** — get board state, get task details, list blocked tasks, compute progress stats, get dependencies for a task
- **Web search tool** — Tavily Search API integration for researching tasks (e.g., find apartments, compare prices, look up regulations)
- **Confirmation flow** — hybrid autonomy model where read-only + non-destructive tools execute immediately, but status changes, adding/removing tasks, modifying dependencies, and deleting subtasks require user confirmation before execution

### Modified Capability: AI Memory (`ai-memory`)
- **Task chat graph** — upgraded from simple respond node to a ReAct agent loop with tool binding
- **Task chat API endpoint** — extended response schema to include tool actions and pending action ID

### Modified Capability: AI Pipeline (`ai-pipeline`)
- **Board chat graph** — new LangGraph graph for board-level AI conversations with board-wide tools

### Modified Capability: Board Management (`board-management`)
- **Board chat endpoint** — new `POST /api/boards/{board_id}/chat` endpoint for board-level AI interactions
- **Task chat response** — extended to include structured tool call results for inline display
- **Pending action model** — new mechanism for storing proposed mutations awaiting user confirmation
- **Confirm/reject action endpoints** — new endpoints for users to approve or reject AI-proposed actions

## Impact
- Affected specs: `ai-tools` (new), `ai-memory` (modified), `ai-pipeline` (modified), `board-management` (modified)
- Affected code:
  - `backend/app/domains/ai/tools/` (new — tool definitions)
  - `backend/app/domains/ai/graphs/chat.py` (modified — ReAct agent loop)
  - `backend/app/domains/ai/graphs/board_chat.py` (new — board chat graph)
  - `backend/app/domains/ai/schemas.py` (modified — tool result schemas)
  - `backend/app/domains/ai/router.py` (modified — board chat endpoint, action endpoints)
  - `backend/app/domains/boards/service.py` (modified — tool execution layer)
  - `backend/app/domains/ai/prompts/chat.py` (modified — tool-aware system prompts)
  - New dependency: `tavily-python` for web search
- No database schema changes required for tools themselves; pending actions require a new table
- No breaking changes to existing API endpoints
