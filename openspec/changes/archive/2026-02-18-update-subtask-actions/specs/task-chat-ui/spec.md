## REMOVED Requirements

### Requirement: AI Actions Section in Task Detail Panel
**Reason**: Task-level AI action buttons are replaced by per-subtask inline action buttons. The separate "AI Actions" section in the TaskDetailPanel is removed.
**Migration**: Remove the `TaskAiActions` component and the "AI Actions" section from `TaskDetailPanel`. Action buttons now appear inline next to each subtask in the SubtaskChecklist.

## MODIFIED Requirements

### Requirement: Chat Section in Task Detail Panel
The system SHALL render a "Chat" section at the bottom of the TaskDetailPanel. The section SHALL contain a message input field and a scrollable message list. Messages SHALL be displayed with sender indication ("You" or "AI"). The chat SHALL use the existing `POST /api/tasks/{task_id}/chat` endpoint. The chat thread persists across page loads via the backend LangGraph checkpointer (thread ID: `task-chat-{task_id}`). The input SHALL be disabled while the AI is responding (loading state). When the AI response contains a `quick_replies` JSON block, the system SHALL render clickable quick-reply buttons below the AI message (see board-ui spec, Quick-Reply Buttons in Chat requirement).

#### Scenario: Send a message in task chat
- **WHEN** a user types "Help me plan this task" and presses Enter (or clicks Send)
- **THEN** the user message appears in the chat, a loading indicator shows, and the AI response appears once received

#### Scenario: Subtask action-triggered chat message
- **WHEN** a user clicks a subtask's inline action button
- **THEN** the action's prompt (prefixed with subtask context) appears as a user message in the chat and the AI response follows

#### Scenario: Chat shows tool actions
- **WHEN** the AI response includes tool actions (e.g., `update_task_field`, `create_subtask`)
- **THEN** the chat displays inline cards for each tool action showing the tool name, description, and status ("executed", "pending", "failed")

#### Scenario: Chat shows pending action confirmation
- **WHEN** the AI response includes a `pending_action_id` (a destructive action awaiting confirmation)
- **THEN** the chat displays a confirmation card with "Confirm" and "Reject" buttons. Clicking "Confirm" calls `POST /api/actions/{id}/confirm` and updates the card status. Clicking "Reject" calls `POST /api/actions/{id}/reject`.

#### Scenario: Chat empty state
- **WHEN** a user opens a task with no prior chat history
- **THEN** the chat section shows a placeholder message like "Ask AI for help with this task, or click an action on a subtask"

#### Scenario: Chat input disabled during response
- **WHEN** a chat message has been sent and the AI is still responding
- **THEN** the input field is disabled and a loading indicator is visible

#### Scenario: Chat shows quick-reply buttons
- **WHEN** the AI response contains a `quick_replies` JSON block with options
- **THEN** clickable buttons appear below the AI message, and clicking one sends its value as the next message
