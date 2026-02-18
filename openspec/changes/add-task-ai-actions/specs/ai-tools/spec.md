## ADDED Requirements

### Requirement: Save Artifact Tool
The system SHALL provide a `save_artifact` tool in the task chat tool registry. The tool SHALL accept parameters: `title` (str, the artifact name), `content` (str, markdown content to save). The tool SHALL create an Artifact record linked to the current task with `created_by: "ai"` and `content_type: "text/markdown"`. The tool SHALL execute immediately (no pending confirmation required, as saving content is non-destructive). The tool SHALL return `{ "status": "executed", "artifact_id": "<id>", "title": "<title>" }` on success. The task chat system prompt SHALL instruct the AI to use this tool when producing substantial, reusable content (agreements, plans, research summaries, comparisons) rather than including long content only in the chat message.

#### Scenario: AI saves generated agreement as artifact
- **WHEN** the AI generates a rental agreement draft during task chat
- **THEN** the AI calls `save_artifact(title="Rental Agreement Draft", content="# Rental Agreement\n...")` and the artifact is persisted to the database

#### Scenario: AI includes artifact in chat response
- **WHEN** the `save_artifact` tool executes successfully
- **THEN** the chat response's `actions` array includes `{ tool_name: "save_artifact", description: "Saved artifact: Rental Agreement Draft", status: "executed", result: { artifact_id: "...", title: "..." } }`

#### Scenario: Save artifact failure
- **WHEN** the `save_artifact` tool encounters a database error
- **THEN** the tool returns `{ "status": "failed", "error": "Failed to save artifact" }` and the AI can inform the user in its response

## MODIFIED Requirements

### Requirement: Tool Registry
The system SHALL provide two functions to assemble context-bound tool lists: `get_task_chat_tools(db, board_id, task_id, user_id, thread_id)` returns tools scoped to a specific task (information retrieval + task mutations + web search + save artifact); `get_board_chat_tools(db, board_id, user_id, thread_id)` returns all task tools plus board-structure tools. Each function SHALL capture `db`, IDs, and `thread_id` via closures so tools execute in the correct context.

#### Scenario: Task chat tools returned
- **WHEN** `get_task_chat_tools` is called with valid IDs
- **THEN** the returned list includes retrieval tools, mutation tools, `save_artifact`, and optionally `web_search`

#### Scenario: Board chat tools returned
- **WHEN** `get_board_chat_tools` is called with valid IDs
- **THEN** the returned list includes all task chat tools plus board-structure tools

#### Scenario: Web search excluded when Tavily not configured
- **WHEN** `TAVILY_API_KEY` is not set
- **THEN** `web_search` is not included in the tool list
