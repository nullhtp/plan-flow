## MODIFIED Requirements

### Requirement: Goal Classification Node
The system SHALL implement a LangGraph node that classifies a goal from raw text input. The classification output SHALL conform to a Pydantic schema containing: `domain` (string — e.g., "relocation", "learning", "product-launch"), `complexity` (integer 1-5), `confidence` (float 0.0-1.0), `dimensions` (list of strings — key aspects to explore), `suggested_title` (a clean, concise title derived from the raw input), and `language` (string — ISO 639-1 language code detected from the input, e.g., "en", "ru", "es", "de"). The classification prompt SHALL be stored as a separate module in `prompts/classify.py`. The detected language SHALL be stored in the goal's `ai_context` and passed to all downstream pipeline nodes so that all AI-generated content is produced in the user's input language. The classification node SHALL accept an optional `user_context` parameter (formatted string from `format_user_meta_block`) and include it in the user prompt alongside the goal text, enabling time-sensitive and location-aware classification.

#### Scenario: Clear goal classified with high confidence
- **WHEN** the classification node receives "Move from Berlin to Lisbon within 3 months"
- **THEN** the output includes a domain (e.g., "relocation"), complexity >= 3, confidence >= 0.7, relevant dimensions (e.g., ["timeline", "budget", "housing", "logistics"]), a suggested title (e.g., "Relocate from Berlin to Lisbon"), and language "en"

#### Scenario: Vague goal classified with low confidence
- **WHEN** the classification node receives "be happier"
- **THEN** the output includes confidence < 0.3 and the `dimensions` list is sparse or generic

#### Scenario: Non-English goal language detected
- **WHEN** the classification node receives a goal in Russian (e.g., "Переехать из Берлина в Лиссабон за 3 месяца")
- **THEN** the output includes language "ru", and the suggested_title is in Russian (e.g., "Переезд из Берлина в Лиссабон")

#### Scenario: Language detection for mixed-language input
- **WHEN** the classification node receives input with mixed languages (e.g., "Move to Лиссабон within 3 months")
- **THEN** the output includes the dominant language detected from the input

#### Scenario: Classification uses user context for time-sensitive goals
- **WHEN** the classification node receives "Plan a birthday party for next Saturday" with user_context containing "Current date: 2026-02-19" and "Day of week: Thursday"
- **THEN** the AI MAY factor the current date and proximity into its complexity and dimension analysis

#### Scenario: Classification without user context (backward compatible)
- **WHEN** the classification node receives a goal without user_context (empty string)
- **THEN** classification proceeds normally as before

### Requirement: User Meta Prompt Injection
The system SHALL format the `UserMeta` context into a standardized text block and inject it into ALL AI prompts: goal classification, question generation, follow-up question generation, board skeleton generation, task enrichment, task chat, board chat, subtask action generation, and sub-board question generation. The meta block SHALL be formatted with the following fields:

```
User context:
- Timezone: {timezone}
- Locale: {locale}
- Current date: {current_date} (formatted as YYYY-MM-DD from current_datetime)
- Day of week: {day_of_week} (e.g., "Thursday", computed from current date and timezone)
- Location: {city}, {country}
- Device: {device_type}
```

Fields with null values SHALL be omitted from the block. If `location` is null, the "Location" line SHALL be omitted. If `user_meta` is not available at all, the entire "User context" block SHALL be omitted (backward compatible). The formatting function SHALL be implemented as a shared utility in `app/domains/ai/prompts/meta.py`. When a memory context block is also present, the user meta block SHALL appear before the memory context block in the prompt.

The `format_user_meta_block()` function SHALL be extended to compute and include the day-of-week name (in English, e.g., "Monday", "Tuesday") from the current date. A new `resolve_user_context()` function SHALL be added to `prompts/meta.py` that accepts a `user_meta` dict (as stored in `goal.ai_context["user_meta"]`), computes the current date and day-of-week server-side from the server clock adjusted to the stored timezone, and returns the formatted context string. This function SHALL be used by chat endpoints and any call site that needs fresh temporal context without requiring the frontend to send it.

For pipeline calls (question generation, board generation, enrichment), the existing `format_user_meta_block()` SHALL continue to be used with the `current_datetime` provided at goal creation time. For chat endpoints and classification, `resolve_user_context()` SHALL be used to ensure the current date is always accurate.

#### Scenario: Full meta injected into prompt with day of week
- **WHEN** the AI generates a board skeleton for a goal with complete `user_meta` (timezone "Europe/Berlin", locale "de-DE", current_datetime "2026-02-19T14:30:00Z", location { city: "Berlin", country: "Germany" }, device_type "desktop")
- **THEN** the user prompt includes a "User context" section with all six fields including "Day of week: Thursday"

#### Scenario: Meta without location injected into prompt
- **WHEN** the AI generates questions for a goal with `user_meta` that has `location: null`
- **THEN** the user prompt includes a "User context" section with timezone, locale, current date, day of week, and device type, but no "Location" line

#### Scenario: No meta available (backward compatible)
- **WHEN** the AI generates a board skeleton for a goal without `user_meta` in `ai_context`
- **THEN** the user prompt does not include a "User context" section and generation proceeds as before

#### Scenario: Meta and memory blocks ordered correctly
- **WHEN** both user meta and memory context are present in a prompt
- **THEN** the "User context" block appears before the "Relevant memories from past interactions" block

#### Scenario: Server-side date resolution for chat
- **WHEN** a chat endpoint resolves user context from a goal created yesterday with timezone "America/New_York"
- **THEN** the "Current date" reflects today's date in the America/New_York timezone and "Day of week" matches that date

#### Scenario: Day of week computed correctly across timezones
- **WHEN** the server time is 2026-02-20 01:00 UTC and the stored timezone is "Pacific/Auckland" (UTC+13, where it is already 2026-02-20 14:00 Friday)
- **THEN** the context block shows "Current date: 2026-02-20" and "Day of week: Friday"

### Requirement: Tool-Aware Chat System Prompts
The system SHALL maintain separate system prompt modules for task chat (`app/domains/ai/prompts/chat.py`) and board chat (`app/domains/ai/prompts/board_chat.py`). The task chat prompt SHALL instruct the AI on available tools (retrieval, mutations, web search, save_artifact), establish its role as a helpful task assistant, and guide appropriate tool usage. The prompt SHALL include instructions to use the `save_artifact` tool when generating substantial, reusable content such as agreements, plans, research summaries, or comparisons — rather than including long content only in the chat message. The board chat prompt SHALL additionally cover structural tools (add/remove tasks and dependencies, split tasks). Both chat prompts SHALL include a `{user_context}` template placeholder that is populated with the formatted user meta block (from `resolve_user_context()`), enabling the AI to reason about the user's timezone, current date, day of week, locale, location, and device during chat interactions.

#### Scenario: Task chat prompt includes tool instructions
- **WHEN** a task chat graph is compiled
- **THEN** the system prompt from `prompts/chat.py` is used, including instructions for all available tools

#### Scenario: Task chat prompt includes artifact instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `save_artifact` for substantial generated content

#### Scenario: Board chat prompt includes structural tool instructions
- **WHEN** a board chat graph is compiled
- **THEN** the system prompt from `prompts/board_chat.py` is used, including instructions for structural tools

#### Scenario: Task chat prompt includes user context
- **WHEN** a task chat prompt is rendered with user_context containing timezone and current date
- **THEN** the rendered system prompt includes the "User context" block with timezone, date, and day of week

#### Scenario: Board chat prompt includes user context
- **WHEN** a board chat prompt is rendered with user_context containing location "Berlin, Germany"
- **THEN** the rendered system prompt includes the "User context" block with the location

#### Scenario: Chat prompt without user context (backward compatible)
- **WHEN** a chat prompt is rendered with an empty user_context string
- **THEN** the prompt renders without a "User context" section

### Requirement: Subtask Action Prompt Module
The system SHALL store the subtask action system prompt in `app/domains/ai/prompts/action_suggestions.py` (repurposed). The prompt SHALL instruct the LLM to: analyze each subtask in the context of the parent task title, description, and status; determine if AI can meaningfully help with each subtask; generate an action (label, icon, prompt) only for automatable subtasks; return null action fields for subtasks requiring physical presence, manual work, or human interaction; use the same language as the task content; vary action types (icons) across subtasks; write the `prompt` field as a natural instruction that references the specific subtask. The prompt SHALL receive the task title, description, status, a list of subtask titles, and the formatted user context block (when available) to enable time-aware and locale-aware action suggestions.

#### Scenario: Prompt stored as module
- **WHEN** the subtask action generation feature is invoked
- **THEN** the system prompt is loaded from `app/domains/ai/prompts/action_suggestions.py`

#### Scenario: Action suggestions use user context
- **WHEN** subtask action generation receives user_context with "Current date: 2026-02-19" and "Locale: de-DE"
- **THEN** the AI MAY factor date proximity and locale into its action suggestions

### Requirement: Board Chat Graph
The system SHALL implement a LangGraph `StateGraph` for board-level AI chat, compiled with the PostgreSQL checkpointer. The graph SHALL share common utilities (should_continue, execute_tools, field extraction) with the task chat graph via `app/domains/ai/graphs/base.py`. The chat graph state SHALL include: `messages` (list of chat messages), `board_id` (string), `user_id` (string), `board_context` (string), `memory_context` (string), `goal_context` (string), and `user_context` (string — formatted user meta block from `resolve_user_context()`). The graph SHALL implement the same ReAct agent loop pattern as the task chat graph. The LLM model SHALL be bound to the board chat tool set via `model.bind_tools(tools)` using tools from the tool registry's `get_board_chat_tools`. The system prompt SHALL instruct the AI about its board-level role. The `respond` node SHALL inject the `user_context` state field into the system prompt via the `{user_context}` template placeholder. Each board's chat session SHALL use a thread ID of format `board-chat-{board_id}`. The graph SHALL be defined in `app/domains/ai/graphs/board_chat.py`. The graph SHALL enforce a maximum of 10 tool-call iterations per turn.

#### Scenario: First message in board chat
- **WHEN** a user sends the first chat message for board "b1" (thread "board-chat-b1")
- **THEN** the graph creates a new thread, injects board context, user context, and memory context, and produces an AI response

#### Scenario: Resuming board chat
- **WHEN** a user sends a second message to a board after a previous conversation
- **THEN** the graph loads the existing thread state from the checkpointer and continues the conversation

#### Scenario: AI uses board structure tool
- **WHEN** a user says "I think we should add a task for getting travel insurance" in board chat
- **THEN** the AI calls `add_task` with appropriate parameters and returns a pending_confirmation result

#### Scenario: AI analyzes board progress
- **WHEN** a user asks "What's my overall progress?" in board chat
- **THEN** the AI calls `get_board_progress`, receives stats, and provides a natural language summary

#### Scenario: AI suggests next actions
- **WHEN** a user asks "What should I work on next?" in board chat
- **THEN** the AI calls `get_blocked_tasks` and `list_all_tasks` to understand the board state, then recommends unlocked tasks based on priority and dependencies

#### Scenario: Shared graph utilities in base module
- **WHEN** the board chat graph needs should_continue or execute_tools logic
- **THEN** it imports these functions from `app/domains/ai/graphs/base.py` rather than reimplementing them

#### Scenario: User context included in board chat
- **WHEN** a user chats about a board and the goal has stored user_meta with timezone "Asia/Tokyo"
- **THEN** the system prompt includes a "User context" block with the current date in the Asia/Tokyo timezone and day of week

### Requirement: Board Chat API Endpoint
The system SHALL expose `POST /api/boards/{board_id}/chat` as an authenticated endpoint that accepts a JSON body with `message` (string). The endpoint SHALL: load the board and its goal context, validate ownership, resolve user context server-side from the goal's stored `user_meta` via `resolve_user_context()`, retrieve relevant memories, obtain the board chat tool set from the tool registry, invoke the board chat graph with the appropriate thread ID and user_context, collect tool actions, and return the enriched chat response conforming to the ChatResponse schema. If the board does not belong to the authenticated user, the endpoint SHALL return 404.

#### Scenario: Successful board chat message
- **WHEN** an authenticated user sends POST /api/boards/{board_id}/chat with body `{"message": "How is the plan looking?"}`
- **THEN** the endpoint returns 200 with the AI's response, tool actions, and thread_id "board-chat-{board_id}"

#### Scenario: Board chat with structural change proposal
- **WHEN** an authenticated user asks the AI to add a task in board chat
- **THEN** the response includes the AI's explanation, a pending_confirmation action, and the pending_action_id

#### Scenario: Unauthorized board access
- **WHEN** a user sends a chat message for another user's board
- **THEN** the endpoint returns 404

#### Scenario: Board not found
- **WHEN** a user sends a chat message for a non-existent board ID
- **THEN** the endpoint returns 404

#### Scenario: Board chat resolves user context from goal
- **WHEN** a user sends a board chat message for a board whose goal has `user_meta` with timezone "Europe/London"
- **THEN** the endpoint resolves the user context server-side with the current date in the Europe/London timezone and passes it to the chat graph

#### Scenario: Board chat without user meta (backward compatible)
- **WHEN** a user sends a board chat message for a board whose goal has no `user_meta`
- **THEN** the endpoint passes an empty string as user_context and chat proceeds normally
