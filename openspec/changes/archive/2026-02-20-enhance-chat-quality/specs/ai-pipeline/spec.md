## MODIFIED Requirements

### Requirement: Board Chat Graph
The system SHALL implement a LangGraph `StateGraph` for board-level AI chat, compiled with the PostgreSQL checkpointer. The graph SHALL share common utilities (should_continue, execute_tools, field extraction) with the task chat graph via `app/domains/ai/graphs/base.py`. The chat graph state SHALL include: `messages` (list of chat messages), `board_id` (string), `user_id` (string), `board_context` (string), `memory_context` (string), `goal_context` (string), and `user_context` (string — formatted user meta block from `resolve_user_context()`). The graph SHALL implement the same ReAct agent loop pattern as the task chat graph. The LLM model SHALL be bound to the board chat tool set via `model.bind_tools(tools)` using tools from the tool registry's `get_board_chat_tools`. The system prompt SHALL instruct the AI about its board-level role. The `respond` node SHALL inject the `user_context` state field into the system prompt via the `{user_context}` template placeholder. Each board's chat session SHALL use a thread ID of format `board-chat-{board_id}`. The graph SHALL be defined in `app/domains/ai/graphs/board_chat.py`. The graph SHALL enforce a maximum of 15 tool-call iterations per turn.

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

#### Scenario: Tool iteration limit enforced at 15
- **WHEN** the AI has made 15 tool calls in a single turn
- **THEN** the graph stops the tool loop and returns the AI's final response without further tool calls
