## MODIFIED Requirements

### Requirement: Task Chat Graph
The system SHALL implement a LangGraph `StateGraph` for task-level AI chat, compiled with the PostgreSQL checkpointer. The chat graph state SHALL include: `messages` (list of chat messages), `task_id` (string), `board_id` (string), `user_id` (string), `task_context` (string — task title, description, subtasks, board context), `memory_context` (string — formatted memory block), and `goal_context` (string — goal text and classification summary). The graph SHALL implement a ReAct agent loop: a `respond` node that produces an AI response (potentially including tool calls), a conditional edge that checks whether the response contains tool calls, a `tool_execute` node that runs the called tools via LangGraph's `ToolNode`, and a loop back to `respond` for the AI to process tool results. The LLM model SHALL be bound to the context-appropriate tool set via `model.bind_tools(tools)` using tools from the tool registry's `get_task_chat_tools`. The `respond` node's system prompt SHALL instruct the AI about available tools, when to use them, and the confirmation flow (that some actions will require user approval). Each task's chat session SHALL use a thread ID of format `task-chat-{task_id}`, enabling conversation persistence across HTTP requests. The graph SHALL be defined in `app/domains/ai/graphs/chat.py`. The graph SHALL enforce a maximum of 10 tool-call iterations per turn to prevent infinite loops.

#### Scenario: First message in task chat
- **WHEN** a user sends the first chat message for task "t1" (thread "task-chat-t1")
- **THEN** the graph creates a new thread, injects task context and memory context, and produces an AI response

#### Scenario: Resuming task chat
- **WHEN** a user sends a second message to task "t1" after a previous conversation
- **THEN** the graph loads the existing thread state (including previous messages) from the checkpointer and continues the conversation

#### Scenario: Task context included in chat
- **WHEN** a user chats about task "Research neighborhoods in Lisbon"
- **THEN** the AI response demonstrates awareness of the task's title, description, subtasks, and the parent goal's context

#### Scenario: Memory context included in chat
- **WHEN** a user with stored memories chats about a task
- **THEN** the AI response MAY reference relevant memories (e.g., "Based on your previous preference for tight budgets...")

#### Scenario: AI uses read-only tool in task chat
- **WHEN** a user asks "What tasks are blocked right now?" in task chat
- **THEN** the AI calls `get_blocked_tasks`, receives the result, and synthesizes it into a natural language response with the tool action included in the response

#### Scenario: AI uses mutation tool requiring confirmation
- **WHEN** a user says "Mark this task as done" in task chat
- **THEN** the AI calls `update_task_status`, receives a pending_confirmation result, and responds explaining the proposed action with the pending_action_id in the response

#### Scenario: AI uses web search in task chat
- **WHEN** a user asks "Can you find apartment listings in Lisbon?" in task chat and Tavily is configured
- **THEN** the AI calls `web_search`, receives structured results, and synthesizes them into a helpful response

#### Scenario: Tool call loop limit enforced
- **WHEN** the AI enters a loop making more than 10 consecutive tool calls in a single turn
- **THEN** the graph breaks the loop and returns the AI's last response

### Requirement: Task Chat API Endpoint
The system SHALL expose a `POST /api/tasks/{task_id}/chat` endpoint that accepts a JSON body with `message` (string). The endpoint SHALL: load the task and its board/goal context, retrieve relevant memories for the user, obtain the task chat tool set from the tool registry, invoke the task chat graph with the appropriate thread ID, collect tool actions from the graph execution, and return the enriched chat response. The response SHALL be a JSON object conforming to the ChatResponse schema: `response` (string — the AI's reply), `thread_id` (string), `actions` (list of ToolAction objects), and `pending_action_id` (nullable string). The endpoint SHALL require authentication. If the task does not belong to the authenticated user's board, the endpoint SHALL return 403.

#### Scenario: Successful chat message with tool usage
- **WHEN** an authenticated user sends POST /api/tasks/{task_id}/chat with body `{"message": "What's blocking this task?"}`
- **THEN** the endpoint returns 200 with `{"response": "...", "thread_id": "task-chat-{task_id}", "actions": [...], "pending_action_id": null}`

#### Scenario: Chat message triggering confirmation
- **WHEN** an authenticated user sends POST /api/tasks/{task_id}/chat with body `{"message": "Start working on this task"}`
- **THEN** the endpoint returns 200 with the AI's response proposing the status change, `actions` containing a pending_confirmation entry, and `pending_action_id` set

#### Scenario: Unauthorized task access
- **WHEN** a user sends a chat message for a task that belongs to another user's board
- **THEN** the endpoint returns 403

#### Scenario: Task not found
- **WHEN** a user sends a chat message for a non-existent task ID
- **THEN** the endpoint returns 404
