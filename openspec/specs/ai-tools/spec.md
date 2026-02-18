# ai-tools Specification

## Purpose
TBD - created by archiving change add-ai-tools. Update Purpose after archive.
## Requirements
### Requirement: Tool Registry
The system SHALL implement a tool registry that maps interaction contexts to available tool sets. Each context (task chat, board chat) SHALL declare which tools are available by returning a list of LangChain tool objects. The registry SHALL be implemented in `app/domains/ai/tools/registry.py`. The registry SHALL expose two functions: `get_task_chat_tools(task_id, board_id, user_id, db_session)` and `get_board_chat_tools(board_id, user_id, db_session)` that return context-bound tool instances with the relevant IDs pre-injected via closures or partial application. If the Tavily API key is not configured, the `web_search` tool SHALL be excluded from all tool sets.

#### Scenario: Task chat tools returned
- **WHEN** `get_task_chat_tools` is called with a valid task, board, and user
- **THEN** the returned list includes information retrieval tools (get_task_details, get_board_overview, get_blocked_tasks, get_task_dependencies), task mutation tools (update_task_field, update_task_status, create_subtask, toggle_subtask, delete_subtask), and optionally web_search

#### Scenario: Board chat tools returned
- **WHEN** `get_board_chat_tools` is called with a valid board and user
- **THEN** the returned list includes all task chat tools plus board structure tools (add_task, remove_task, add_dependency, remove_dependency, split_task, list_all_tasks, get_board_progress)

#### Scenario: Web search excluded when Tavily not configured
- **WHEN** the `TAVILY_API_KEY` environment variable is not set
- **THEN** the `web_search` tool is not included in any tool set

### Requirement: Information Retrieval Tools
The system SHALL implement read-only tools that allow the AI to query board and task state. These tools SHALL execute immediately without confirmation. All tools SHALL be defined in `app/domains/ai/tools/retrieval.py` using the `@tool` decorator from `langchain_core.tools`. Each tool SHALL validate that the requested data belongs to the authenticated user's board.

The following retrieval tools SHALL be implemented:
- `get_task_details(task_id)` — returns task title, description, status, is_locked, priority, due_date, estimated_minutes, subtasks, dependency_ids, dependent_ids
- `get_board_overview(board_id)` — returns board title, total tasks, completed tasks, in-progress tasks, blocked tasks count
- `get_blocked_tasks(board_id)` — returns list of locked tasks with their blocking dependency names
- `get_task_dependencies(task_id)` — returns the task's prerequisite tasks and dependent tasks with their statuses
- `list_all_tasks(board_id)` — returns all tasks on the board with id, title, status, is_locked, is_goal_node
- `get_board_progress(board_id)` — returns completion percentage, tasks by status counts, estimated time remaining (sum of incomplete task estimates)

#### Scenario: Get task details for own task
- **WHEN** the AI calls `get_task_details` for a task on the user's board
- **THEN** the tool returns a dict with the task's full details including subtasks and dependencies

#### Scenario: Get board overview
- **WHEN** the AI calls `get_board_overview` for the user's board
- **THEN** the tool returns a summary dict with task counts by status and board title

#### Scenario: Get blocked tasks
- **WHEN** the AI calls `get_blocked_tasks` for a board with 3 locked tasks
- **THEN** the tool returns a list of 3 tasks with their blocking dependency names

#### Scenario: Get board progress with estimates
- **WHEN** the AI calls `get_board_progress` for a board where 5 of 10 tasks are done and remaining tasks have estimated_minutes
- **THEN** the tool returns completion percentage (50%), status counts, and total estimated minutes remaining

### Requirement: Task Mutation Tools
The system SHALL implement tools that allow the AI to modify task data. Tools SHALL be defined in `app/domains/ai/tools/mutations.py` using the `@tool` decorator. Each tool SHALL validate ownership and enforce the same business rules as the existing REST endpoints.

The following mutation tools SHALL be implemented:
- `update_task_field(task_id, field, value)` — updates a single non-status field (title, description, due_date, priority, estimated_minutes). Executes immediately without confirmation.
- `update_task_status(task_id, new_status)` — changes task status with the same dependency validation as the PATCH endpoint. **Requires confirmation.**
- `create_subtask(task_id, title)` — creates a new subtask. Executes immediately.
- `toggle_subtask(subtask_id)` — toggles subtask completed status. Executes immediately.
- `delete_subtask(subtask_id)` — deletes a subtask. **Requires confirmation.**

#### Scenario: AI updates task description immediately
- **WHEN** the AI calls `update_task_field(task_id, "description", "Updated description")`
- **THEN** the task description is updated in the database and the tool returns a success result with the updated field

#### Scenario: AI proposes status change requiring confirmation
- **WHEN** the AI calls `update_task_status(task_id, "in_progress")`
- **THEN** the tool does NOT execute the status change but creates a PendingAction record and returns a result indicating confirmation is needed

#### Scenario: AI status change respects dependency rules
- **WHEN** the AI calls `update_task_status(task_id, "in_progress")` for a task with unmet dependencies
- **THEN** the tool returns an error result explaining that dependencies must be completed first, without creating a PendingAction

#### Scenario: AI creates subtask immediately
- **WHEN** the AI calls `create_subtask(task_id, "Research visa options")`
- **THEN** a new subtask is created and the tool returns the subtask details

#### Scenario: AI proposes subtask deletion requiring confirmation
- **WHEN** the AI calls `delete_subtask(subtask_id)`
- **THEN** the tool creates a PendingAction and returns a confirmation-needed result

### Requirement: Board Structure Tools
The system SHALL implement tools that allow the AI to modify the board's task graph structure. Tools SHALL be defined in `app/domains/ai/tools/structure.py` using the `@tool` decorator. All structure tools **require confirmation** except when noted.

The following structure tools SHALL be implemented:
- `add_task(board_id, title, description, depends_on_ids, dependent_ids)` — adds a new task to the board with specified dependency edges. **Requires confirmation.** The tool SHALL validate that the resulting graph remains a valid DAG.
- `remove_task(task_id)` — removes a task and all its dependency edges. **Requires confirmation.** The tool SHALL prevent removal of the goal node.
- `add_dependency(dependent_task_id, dependency_task_id)` — adds a dependency edge between two tasks. **Requires confirmation.** The tool SHALL validate that adding the edge does not create a cycle.
- `remove_dependency(dependent_task_id, dependency_task_id)` — removes a dependency edge. **Requires confirmation.**
- `split_task(task_id, new_tasks)` — splits one task into multiple tasks, preserving the original's dependency edges. **Requires confirmation.** The new tasks inherit the original task's incoming dependencies and the original's dependents point to the last new task (or the AI specifies the wiring).

#### Scenario: AI proposes adding a task
- **WHEN** the AI calls `add_task(board_id, "Book temporary accommodation", "Find short-term rental", depends_on_ids=["task-uuid-1"], dependent_ids=["task-uuid-2"])`
- **THEN** the tool validates the DAG would remain valid, creates a PendingAction with the full task specification, and returns a confirmation-needed result

#### Scenario: AI proposes removing a task
- **WHEN** the AI calls `remove_task(task_id)` for a non-goal-node task
- **THEN** the tool creates a PendingAction and returns a confirmation-needed result describing what will be removed

#### Scenario: AI cannot remove goal node
- **WHEN** the AI calls `remove_task(task_id)` for the goal node
- **THEN** the tool returns an error result explaining that the goal node cannot be removed

#### Scenario: AI proposes adding a dependency that would create a cycle
- **WHEN** the AI calls `add_dependency(task_a, task_b)` where task_b already transitively depends on task_a
- **THEN** the tool returns an error result explaining that the dependency would create a cycle, without creating a PendingAction

#### Scenario: AI proposes splitting a task
- **WHEN** the AI calls `split_task(task_id, [{"title": "Part 1", "description": "..."}, {"title": "Part 2", "description": "..."}])`
- **THEN** the tool creates a PendingAction describing the split operation and returns a confirmation-needed result

### Requirement: Web Search Tool
The system SHALL implement a web search tool using the Tavily Search API (`tavily-python`). The tool SHALL be defined in `app/domains/ai/tools/web_search.py` using the `@tool` decorator. The tool accepts a `query` (string) and optional `max_results` (integer, default 5). The tool SHALL return structured results: a list of objects with `title`, `url`, `content` (snippet), and `score` (relevance). The tool executes immediately without confirmation. The Tavily API key SHALL be read from the `TAVILY_API_KEY` environment variable. If the API call fails, the tool SHALL return an error result with a user-friendly message. The AI's system prompt SHALL instruct it to use web search only when the user asks for research help or when external information is genuinely needed.

#### Scenario: Successful web search
- **WHEN** the AI calls `web_search("apartment rental prices Lisbon 2026")`
- **THEN** the tool returns a list of up to 5 results with titles, URLs, content snippets, and relevance scores

#### Scenario: Web search API failure
- **WHEN** the Tavily API returns an error or times out
- **THEN** the tool returns an error result with message "Web search is temporarily unavailable" and the AI can inform the user

#### Scenario: Web search with custom result count
- **WHEN** the AI calls `web_search("visa requirements Portugal", max_results=3)`
- **THEN** the tool returns at most 3 results

### Requirement: Tool Confirmation Flow
The system SHALL implement a hybrid autonomy model where certain tool calls require user confirmation before execution. The confirmation status SHALL be communicated inline in the chat response. The system SHALL store pending actions in a `pending_action` database table.

**Tools requiring confirmation:** `update_task_status`, `add_task`, `remove_task`, `add_dependency`, `remove_dependency`, `delete_subtask`, `split_task`.

**Tools executing immediately:** `get_task_details`, `get_board_overview`, `get_blocked_tasks`, `get_task_dependencies`, `list_all_tasks`, `get_board_progress`, `update_task_field`, `create_subtask`, `toggle_subtask`, `web_search`.

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

### Requirement: Pending Action Data Model
The system SHALL store pending actions in a `pending_action` PostgreSQL table with the following columns: `id` (UUID primary key), `user_id` (FK to user, indexed), `thread_id` (string — the chat thread that proposed this action, indexed), `tool_name` (string — which tool was called), `tool_args` (JSON — the arguments passed to the tool), `description` (string — human-readable description of the proposed action), `status` (string enum: `pending` / `confirmed` / `rejected` / `expired`, default `pending`), `result` (JSON, nullable — the execution result after confirmation), `created_at` (datetime with timezone), `expires_at` (datetime with timezone — 10 minutes after created_at). The table SHALL be defined as a SQLModel model in `app/domains/ai/models.py`. An Alembic migration SHALL create this table.

#### Scenario: Pending action created for status change
- **WHEN** the AI proposes changing a task status
- **THEN** a PendingAction row is created with the tool name, args, description, status `pending`, and expires_at set to 10 minutes from now

#### Scenario: Pending action belongs to user
- **WHEN** pending actions are queried
- **THEN** only actions belonging to the authenticated user are returned

### Requirement: Confirm Action Endpoint
The system SHALL expose `POST /api/actions/{action_id}/confirm` as an authenticated endpoint that executes a pending action. The endpoint SHALL validate: the action belongs to the authenticated user, the action status is `pending`, and the action has not expired (current time < expires_at). Upon confirmation, the endpoint SHALL execute the stored tool call (using tool_name and tool_args), update the PendingAction status to `confirmed`, store the execution result in the `result` column, and return the result. If execution fails (e.g., task was modified between proposal and confirmation), the endpoint SHALL return the error and set status to `rejected`.

#### Scenario: Successfully confirm a status change
- **WHEN** a user sends `POST /api/actions/{action_id}/confirm` for a pending status change action
- **THEN** the task status is updated, the PendingAction status becomes `confirmed`, and the response includes the execution result

#### Scenario: Confirm expired action
- **WHEN** a user confirms an action whose `expires_at` is in the past
- **THEN** the endpoint returns 410 (Gone) with a message that the action has expired

#### Scenario: Confirm already confirmed action
- **WHEN** a user confirms an action with status `confirmed`
- **THEN** the endpoint returns 409 (Conflict) with a message that the action was already confirmed

#### Scenario: Confirm action for another user
- **WHEN** user A confirms an action belonging to user B
- **THEN** the endpoint returns 404

#### Scenario: Execution fails at confirmation time
- **WHEN** a user confirms a status change but the task's dependencies are no longer met (state changed since proposal)
- **THEN** the endpoint returns 409 with the validation error, and the PendingAction status is set to `rejected`

### Requirement: Reject Action Endpoint
The system SHALL expose `POST /api/actions/{action_id}/reject` as an authenticated endpoint that rejects a pending action without executing it. The endpoint SHALL validate ownership and that the action is still `pending`. Upon rejection, the PendingAction status SHALL be set to `rejected`.

#### Scenario: Successfully reject an action
- **WHEN** a user sends `POST /api/actions/{action_id}/reject` for a pending action
- **THEN** the PendingAction status becomes `rejected` and the response confirms the rejection

#### Scenario: Reject non-pending action
- **WHEN** a user rejects an action with status `confirmed`
- **THEN** the endpoint returns 409 (Conflict)

### Requirement: Chat Response Schema with Tool Actions
The chat response for both task chat and board chat endpoints SHALL include structured tool action data alongside the natural language response. The response schema SHALL include: `response` (string — AI's natural language reply), `thread_id` (string), `actions` (list of ToolAction objects — tools used in this turn), and `pending_action_id` (nullable string — set when a confirmable action was proposed). Each ToolAction SHALL contain: `tool_name` (string), `description` (string — human-readable), `status` (string — one of "executed", "pending_confirmation", "failed"), and `result` (nullable dict — tool-specific result data for executed tools, null for pending/failed). This schema enables the frontend to render inline action cards showing what the AI did or proposed.

#### Scenario: Response with executed read-only tool
- **WHEN** the AI uses `get_board_overview` and then responds
- **THEN** the response includes `actions: [{"tool_name": "get_board_overview", "description": "Retrieved board overview", "status": "executed", "result": {...}}]` and a natural language summary

#### Scenario: Response with pending confirmation
- **WHEN** the AI proposes a status change
- **THEN** the response includes `actions: [{"tool_name": "update_task_status", "description": "Mark task 'Research flights' as done", "status": "pending_confirmation", "result": null}]` and `pending_action_id` is set

#### Scenario: Response with no tool usage
- **WHEN** the AI responds to a simple question without using tools
- **THEN** the response includes `actions: []` and `pending_action_id: null`

#### Scenario: Response with multiple tool actions
- **WHEN** the AI uses `get_task_dependencies` and then `get_blocked_tasks` before responding
- **THEN** the response includes both tool actions in the `actions` array in execution order

### Requirement: Tavily Configuration
The system SHALL add the following settings to the application configuration: `TAVILY_API_KEY` (string, nullable, default: null) — API key for Tavily Search. When null, web search tools are excluded from all tool sets. `AI_WEB_SEARCH_MAX_RESULTS` (integer, default: 5) — maximum results per web search call.

#### Scenario: Tavily configured
- **WHEN** `TAVILY_API_KEY` is set to a valid API key
- **THEN** the web_search tool is available in task and board chat tool sets

#### Scenario: Tavily not configured
- **WHEN** `TAVILY_API_KEY` is not set
- **THEN** web_search tool is excluded and the AI cannot search the web

#### Scenario: Custom max results
- **WHEN** `AI_WEB_SEARCH_MAX_RESULTS` is set to 3
- **THEN** web search returns at most 3 results per call

### Requirement: Tool Execution Safety
All tool functions that mutate data SHALL execute within database transactions. If a tool execution fails, the transaction SHALL be rolled back and the tool SHALL return a structured error result (not raise an exception). The error result SHALL include a `status: "failed"` flag and a human-readable `error` message that the AI can relay to the user. Tools SHALL never expose internal error details (stack traces, SQL errors) to the AI or user — only sanitized, user-friendly messages.

#### Scenario: Tool mutation rolls back on failure
- **WHEN** a tool execution encounters a database error mid-transaction
- **THEN** the transaction is rolled back, no data is modified, and the tool returns `{"status": "failed", "error": "Unable to update task. Please try again."}`

#### Scenario: Tool returns user-friendly error
- **WHEN** a tool validation fails (e.g., task not found, unauthorized)
- **THEN** the tool returns a structured error without exposing internal details

