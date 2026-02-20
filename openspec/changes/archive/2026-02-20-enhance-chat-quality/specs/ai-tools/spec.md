## ADDED Requirements

### Requirement: Update Artifact Tool
The system SHALL provide an `update_artifact` tool in the task chat and board chat tool registries. The tool SHALL accept parameters: `artifact_id` (str, UUID of the existing artifact), `title` (str, the new title), `content` (str, the new markdown content — full replacement). The tool SHALL validate that the artifact exists and belongs to a task on the user's board. The tool SHALL replace the artifact's `title` and `content` entirely with the new values and update the `updated_at` timestamp. The tool SHALL execute immediately without confirmation (non-destructive — content is replaced, artifact record persists). The tool SHALL return `{ "status": "executed", "artifact_id": "<id>", "title": "<new_title>" }` on success. In task chat, the tool operates on artifacts of the current task. In board chat, the tool accepts any artifact on the board (the AI SHALL use retrieval tools to discover artifact IDs when needed). The tool SHALL be defined in `app/domains/ai/tools/mutations.py` as `make_update_artifact()`.

#### Scenario: AI updates an existing artifact
- **WHEN** the AI calls `update_artifact(artifact_id="abc-123", title="Rental Agreement v2", content="# Updated Agreement\n...")`
- **THEN** the artifact's title and content are replaced, `updated_at` is set to current time, and the tool returns success with the artifact ID

#### Scenario: AI updates artifact that doesn't exist
- **WHEN** the AI calls `update_artifact(artifact_id="nonexistent", title="X", content="Y")`
- **THEN** the tool returns `{ "status": "failed", "error": "Artifact not found" }`

#### Scenario: AI updates artifact on another user's board
- **WHEN** the AI calls `update_artifact` for an artifact on a task that belongs to a different user
- **THEN** the tool returns `{ "status": "failed", "error": "Artifact not found" }`

#### Scenario: Update artifact failure rolls back
- **WHEN** the `update_artifact` tool encounters a database error during the update
- **THEN** the transaction is rolled back and the tool returns `{ "status": "failed", "error": "Unable to update artifact. Please try again." }`

## MODIFIED Requirements

### Requirement: Tool Registry
The system SHALL provide two functions to assemble context-bound tool lists: `get_task_chat_tools(db, board_id, task_id, user_id, thread_id)` returns tools scoped to a specific task (information retrieval + task mutations + web search + URL fetch + save artifact + update artifact); `get_board_chat_tools(db, board_id, user_id, thread_id)` returns all task tools plus board-structure tools plus save artifact and update artifact. Each function SHALL capture `db`, IDs, and `thread_id` via closures so tools execute in the correct context.

#### Scenario: Task chat tools returned
- **WHEN** `get_task_chat_tools` is called with valid IDs
- **THEN** the returned list includes retrieval tools, mutation tools, `save_artifact`, `update_artifact`, `fetch_url_content`, and optionally `web_search`

#### Scenario: Board chat tools returned
- **WHEN** `get_board_chat_tools` is called with valid IDs
- **THEN** the returned list includes all task-level retrieval tools, board-wide retrieval tools, task mutation tools, board-structure tools, `save_artifact`, `update_artifact`, `fetch_url_content`, and optionally `web_search`

#### Scenario: Web search excluded when Tavily not configured
- **WHEN** `TAVILY_API_KEY` is not set
- **THEN** `web_search` is not included in the tool list but `fetch_url_content` is still available

### Requirement: Tool Confirmation Flow
The system SHALL implement a hybrid autonomy model where certain tool calls require user confirmation before execution. The confirmation status SHALL be communicated inline in the chat response. The system SHALL store pending actions in a `pending_action` database table.

**Tools requiring confirmation:** `update_task_status`, `add_task`, `remove_task`, `add_dependency`, `remove_dependency`, `delete_subtask`, `split_task`.

**Tools executing immediately:** `get_task_details`, `get_board_overview`, `get_blocked_tasks`, `get_task_dependencies`, `list_all_tasks`, `get_board_progress`, `update_task_field`, `create_subtask`, `toggle_subtask`, `web_search`, `fetch_url_content`, `save_artifact`, `update_artifact`.

When a confirmable tool is called, the tool function SHALL: (1) validate the action is possible (e.g., check DAG validity, ownership, business rules), (2) if validation fails, return an error result without creating a PendingAction, (3) if validation passes, create a PendingAction record, and (4) return a result with `status: "pending_confirmation"`, the `pending_action_id`, and a human-readable `description` of the proposed action.

Only one PendingAction with status `pending` SHALL exist per thread at a time. If a new confirmable tool is called while a pending action exists, the old pending action SHALL be automatically set to `expired`.

The `app/domains/ai/pending_actions.py` module SHALL delegate all data mutations to the boards domain services (`boards/task_service.py`, `boards/subtask_service.py`) instead of reimplementing business logic. Status transition validation, task deletion, and subtask operations SHALL have a single source of truth in the boards domain.

#### Scenario: Confirmable tool creates pending action
- **WHEN** the AI calls `update_task_status(task_id, "done")` and validation passes
- **THEN** a PendingAction record is created with status `pending`, tool_name `update_task_status`, tool_args `{"task_id": "...", "new_status": "done"}`, and a description like "Mark task 'Research flights' as done"

#### Scenario: Only one pending action per thread
- **WHEN** a pending action exists for thread "task-chat-123" and the AI calls another confirmable tool
- **THEN** the existing pending action is set to `expired` and a new one is created

#### Scenario: Pending action auto-expires
- **WHEN** a PendingAction has been in `pending` status for more than 10 minutes
- **THEN** the action is treated as expired and SHALL NOT be executable

#### Scenario: Validation failure prevents pending action creation
- **WHEN** the AI calls `add_dependency(a, b)` but it would create a cycle
- **THEN** no PendingAction is created and the tool returns an error result

#### Scenario: Pending action execution delegates to boards service
- **WHEN** a pending action for `update_task_status` is confirmed
- **THEN** the execution calls `boards/task_service.py` for the status transition, using the same validation logic as the REST endpoint

### Requirement: Tool-Aware Chat System Prompts
The system SHALL maintain separate system prompt modules for task chat (`app/domains/ai/prompts/chat.py`) and board chat (`app/domains/ai/prompts/board_chat.py`). Both prompts SHALL enforce a "smart mode" response pattern: short conversational replies (1-3 sentences) for simple questions and brief guidance; automatic artifact creation via `save_artifact` when the AI generates substantial, reusable content (plans, research summaries, comparisons, templates, checklists, agreements, analyses — generally any document-like content exceeding a few sentences). When saving an artifact, the chat message SHALL contain only a brief summary referencing the saved artifact, not the full content.

The task chat prompt SHALL instruct the AI on available tools (retrieval, mutations, web search, URL fetch, save_artifact, update_artifact), establish its role as a helpful task assistant, and guide appropriate tool usage. The prompt SHALL include explicit artifact quality guidelines: artifacts MUST use proper markdown structure (headings, subheadings, tables, bullet points, code blocks as appropriate), provide thorough and comprehensive coverage of the topic, and be actionable and ready to use. The prompt SHALL include instructions to use `update_artifact` when the user asks to revise, improve, or regenerate an existing artifact. The prompt SHALL include instructions to use `fetch_url_content` when the user shares a URL or when the AI wants to examine a search result in detail, and to cite sources with URLs when using information from web search or fetched pages.

The board chat prompt SHALL additionally cover structural tools (add/remove tasks and dependencies, split tasks) and artifact tools (`save_artifact`, `update_artifact`) with the note that these require a `task_id` parameter to identify which task to save the artifact on. Both chat prompts SHALL include a `{user_context}` template placeholder that is populated with the formatted user meta block (from `resolve_user_context()`), enabling the AI to reason about the user's timezone, current date, day of week, locale, location, and device during chat interactions.

#### Scenario: Task chat prompt includes tool instructions
- **WHEN** a task chat graph is compiled
- **THEN** the system prompt from `prompts/chat.py` is used, including instructions for all available tools

#### Scenario: Task chat prompt includes artifact instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `save_artifact` for substantial generated content and to keep chat messages concise when an artifact is saved

#### Scenario: Task chat prompt includes artifact quality guidelines
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes explicit guidelines for artifact quality: proper markdown structure, thorough coverage, actionable content

#### Scenario: Task chat prompt includes update artifact instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `update_artifact` when the user asks to revise or improve an existing artifact

#### Scenario: Task chat prompt includes URL fetch instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `fetch_url_content` for examining URLs and diving deeper into search results

#### Scenario: Board chat prompt includes structural tool instructions
- **WHEN** a board chat graph is compiled
- **THEN** the system prompt from `prompts/board_chat.py` is used, including instructions for structural tools

#### Scenario: Board chat prompt includes artifact tools
- **WHEN** the board chat system prompt is loaded
- **THEN** it includes instructions for `save_artifact` and `update_artifact` with guidance on specifying `task_id`

#### Scenario: Task chat prompt includes user context
- **WHEN** a task chat prompt is rendered with user_context containing timezone and current date
- **THEN** the rendered system prompt includes the "User context" block with timezone, date, and day of week

#### Scenario: Board chat prompt includes user context
- **WHEN** a board chat prompt is rendered with user_context containing location "Berlin, Germany"
- **THEN** the rendered system prompt includes the "User context" block with the location

#### Scenario: Chat prompt without user context (backward compatible)
- **WHEN** a chat prompt is rendered with an empty user_context string
- **THEN** the prompt renders without a "User context" section
