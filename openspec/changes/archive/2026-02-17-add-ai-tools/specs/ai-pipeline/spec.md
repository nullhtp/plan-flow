## ADDED Requirements

### Requirement: Board Chat Graph
The system SHALL implement a LangGraph `StateGraph` for board-level AI chat, compiled with the PostgreSQL checkpointer. The chat graph state SHALL include: `messages` (list of chat messages), `board_id` (string), `user_id` (string), `board_context` (string — board title, task summary, progress stats), `memory_context` (string — formatted memory block), and `goal_context` (string — goal text and classification summary). The graph SHALL implement the same ReAct agent loop pattern as the task chat graph. The LLM model SHALL be bound to the board chat tool set via `model.bind_tools(tools)` using tools from the tool registry's `get_board_chat_tools`. The system prompt SHALL instruct the AI about its board-level role: helping users manage their plan, reorganize priorities, identify blockers, and make structural changes. Each board's chat session SHALL use a thread ID of format `board-chat-{board_id}`. The graph SHALL be defined in `app/domains/ai/graphs/board_chat.py`. The graph SHALL enforce a maximum of 10 tool-call iterations per turn.

#### Scenario: First message in board chat
- **WHEN** a user sends the first chat message for board "b1" (thread "board-chat-b1")
- **THEN** the graph creates a new thread, injects board context and memory context, and produces an AI response

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

### Requirement: Board Chat API Endpoint
The system SHALL expose `POST /api/boards/{board_id}/chat` as an authenticated endpoint that accepts a JSON body with `message` (string). The endpoint SHALL: load the board and its goal context, validate ownership, retrieve relevant memories, obtain the board chat tool set from the tool registry, invoke the board chat graph with the appropriate thread ID, collect tool actions, and return the enriched chat response conforming to the ChatResponse schema. If the board does not belong to the authenticated user, the endpoint SHALL return 404.

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

### Requirement: AI Chat Model Configuration
The system SHALL add an `AI_CHAT_MODEL` setting (string, default: same as `AI_DEFAULT_MODEL`) to the application configuration. This setting allows using a different model for chat interactions that is optimized for tool calling. The task chat and board chat graphs SHALL use this model instead of the default model.

#### Scenario: Separate chat model configured
- **WHEN** `AI_CHAT_MODEL` is set to "anthropic/claude-sonnet-4"
- **THEN** the task chat and board chat graphs use "anthropic/claude-sonnet-4" for LLM calls

#### Scenario: Chat model defaults to pipeline model
- **WHEN** `AI_CHAT_MODEL` is not set
- **THEN** the chat graphs use the value of `AI_DEFAULT_MODEL`

### Requirement: Tool-Aware Chat System Prompts
The system SHALL update the task chat system prompt and create a board chat system prompt that instruct the AI about tool usage. The prompts SHALL be stored in `app/domains/ai/prompts/chat.py` (updated) and `app/domains/ai/prompts/board_chat.py` (new). The prompts SHALL instruct the AI to: (1) use tools proactively when they can help answer the user's question or fulfill their request, (2) prefer reading board state via tools over making assumptions, (3) explain what it's doing when using tools, (4) clearly communicate when an action requires user confirmation, (5) use web search only when the user asks for research or when external info is genuinely needed, and (6) never fabricate tool results.

#### Scenario: Task chat prompt includes tool instructions
- **WHEN** the task chat system prompt is constructed
- **THEN** it includes instructions about available tools, when to use them, and confirmation behavior

#### Scenario: Board chat prompt includes structural tool instructions
- **WHEN** the board chat system prompt is constructed
- **THEN** it includes instructions about board-wide tools including adding/removing tasks and managing dependencies
