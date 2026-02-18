## ADDED Requirements

### Requirement: AI Actions Section in Task Detail Panel
The system SHALL render an "AI Actions" section in the TaskDetailPanel, positioned after the Subtasks section. When the user opens a task, the system SHALL call `POST /api/tasks/{task_id}/actions/suggest` and display a loading skeleton while waiting. Once loaded, 2–4 action buttons SHALL be displayed in a responsive grid (2 columns on normal width, 1 column on narrow). Each button SHALL display the action's `label` and an icon corresponding to the `icon` hint. A refresh button SHALL allow the user to regenerate suggestions (re-calls the endpoint). Clicking an action button SHALL send the action's `prompt` to the task chat endpoint and scroll to the chat section.

#### Scenario: Actions loaded on task open
- **WHEN** a user opens the task detail panel for a task
- **THEN** the AI Actions section shows a loading skeleton, then displays 2–4 action buttons once the LLM responds

#### Scenario: User clicks an action button
- **WHEN** a user clicks an action button with prompt "Generate agreement draft"
- **THEN** the prompt is sent to `POST /api/tasks/{task_id}/chat` as a message, the chat section shows a loading indicator, and the AI response appears in the chat section

#### Scenario: User refreshes action suggestions
- **WHEN** a user clicks the refresh button in the AI Actions section
- **THEN** the current suggestions are replaced with a loading skeleton and new suggestions are fetched

#### Scenario: Action suggestion fetch fails
- **WHEN** the action suggestion endpoint returns an error
- **THEN** the AI Actions section shows an error state with a retry button

### Requirement: Artifacts Section in Task Detail Panel
The system SHALL render an "Artifacts" section in the TaskDetailPanel, positioned after the AI Actions section. The section SHALL list all artifacts for the task, fetched via `GET /api/tasks/{task_id}/artifacts`. Each artifact SHALL display its title, a "copy" button (copies markdown content to clipboard), and a "delete" button. Clicking an artifact title SHALL expand/collapse the artifact content rendered as formatted markdown. The section SHALL show "No artifacts yet" when the list is empty.

#### Scenario: Artifacts displayed for a task
- **WHEN** a user opens a task with 2 artifacts
- **THEN** the Artifacts section lists both artifacts with their titles

#### Scenario: Expand artifact content
- **WHEN** a user clicks an artifact title
- **THEN** the artifact content expands below the title, rendered as formatted markdown

#### Scenario: Copy artifact content
- **WHEN** a user clicks the copy button on an artifact
- **THEN** the artifact's markdown content is copied to the clipboard and a success toast is shown

#### Scenario: Delete artifact
- **WHEN** a user clicks the delete button on an artifact and confirms
- **THEN** the artifact is removed optimistically and a DELETE request is sent

#### Scenario: No artifacts
- **WHEN** a user opens a task with no artifacts
- **THEN** the Artifacts section shows "No artifacts yet" placeholder text

### Requirement: Chat Section in Task Detail Panel
The system SHALL render a "Chat" section at the bottom of the TaskDetailPanel. The section SHALL contain a message input field and a scrollable message list. Messages SHALL be displayed with sender indication ("You" or "AI"). The chat SHALL use the existing `POST /api/tasks/{task_id}/chat` endpoint. The chat thread persists across page loads via the backend LangGraph checkpointer (thread ID: `task-chat-{task_id}`). The input SHALL be disabled while the AI is responding (loading state).

#### Scenario: Send a message in task chat
- **WHEN** a user types "Help me plan this task" and presses Enter (or clicks Send)
- **THEN** the user message appears in the chat, a loading indicator shows, and the AI response appears once received

#### Scenario: Action-triggered chat message
- **WHEN** a user clicks an AI action button
- **THEN** the action's prompt appears as a user message in the chat and the AI response follows

#### Scenario: Chat shows tool actions
- **WHEN** the AI response includes tool actions (e.g., `update_task_field`, `create_subtask`)
- **THEN** the chat displays inline cards for each tool action showing the tool name, description, and status ("executed", "pending", "failed")

#### Scenario: Chat shows pending action confirmation
- **WHEN** the AI response includes a `pending_action_id` (a destructive action awaiting confirmation)
- **THEN** the chat displays a confirmation card with "Confirm" and "Reject" buttons. Clicking "Confirm" calls `POST /api/actions/{id}/confirm` and updates the card status. Clicking "Reject" calls `POST /api/actions/{id}/reject`.

#### Scenario: Chat empty state
- **WHEN** a user opens a task with no prior chat history
- **THEN** the chat section shows a placeholder message like "Ask AI for help with this task, or click an action above"

#### Scenario: Chat input disabled during response
- **WHEN** a chat message has been sent and the AI is still responding
- **THEN** the input field is disabled and a loading indicator is visible

### Requirement: Board Data Invalidation After Chat Actions
The system SHALL invalidate and refetch the board query after any chat response that includes tool actions with status "executed" or after a pending action is confirmed. This ensures task mutations performed by the AI (status changes, subtask creation, field updates) are reflected in the DAG view and task detail panel.

#### Scenario: Board refetched after AI tool execution
- **WHEN** an AI chat response includes a tool action with status "executed" that modified task data
- **THEN** the board React Query cache is invalidated and the board data is refetched

#### Scenario: Board refetched after pending action confirmed
- **WHEN** a user confirms a pending action and the confirmation succeeds
- **THEN** the board React Query cache is invalidated and the board data is refetched

### Requirement: Artifact Creation Triggers Refresh
The system SHALL refetch the artifacts list after any chat response that includes a `save_artifact` tool action with status "executed". This ensures newly created artifacts appear in the Artifacts section without manual refresh.

#### Scenario: New artifact appears after AI generates content
- **WHEN** the AI chat response includes a `save_artifact` tool action with status "executed"
- **THEN** the Artifacts section refetches and displays the newly created artifact
