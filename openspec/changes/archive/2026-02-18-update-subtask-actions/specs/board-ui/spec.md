## MODIFIED Requirements

### Requirement: Subtask Checklist in Detail Panel
The system SHALL render subtasks as a checklist within the task detail side panel. Each subtask SHALL display a checkbox (toggle completed) and the subtask title. When a subtask has a non-null `action_prompt`, a small action button (sparkle/wand icon) SHALL appear inline next to the subtask title. Clicking the action button SHALL send the subtask's `action_prompt` to the task chat, prefixed with the subtask context (e.g., "Help me with subtask: {subtask_title} -- {action_prompt}"), and scroll to the chat section. A loading indicator SHALL appear on the action button while the subtask's action is being generated (after manual subtask creation). Users SHALL be able to add new subtasks via an inline text input at the bottom of the list, toggle completion, edit subtask titles inline, and delete subtasks. All operations SHALL use optimistic updates. When a user adds a new subtask, the system SHALL call the action generation endpoint in the background and update the subtask's action button once the result is available.

#### Scenario: Toggle subtask completion
- **WHEN** a user clicks the checkbox on a subtask
- **THEN** the checkbox toggles immediately (optimistic) and a PATCH request updates the `completed` field

#### Scenario: Add subtask
- **WHEN** a user types a subtask title in the input and presses Enter
- **THEN** the subtask appears in the list immediately (optimistic), a POST request creates it on the server, and an action generation request is triggered in the background

#### Scenario: Delete subtask
- **WHEN** a user clicks the delete button on a subtask
- **THEN** the subtask is removed from the list immediately (optimistic) and a DELETE request removes it on the server

#### Scenario: Subtask with AI action button
- **WHEN** a subtask has `action_label: "Generate agreement draft"` and `action_icon: "generate"`
- **THEN** a sparkle/wand icon button appears next to the subtask title with a tooltip showing the action label

#### Scenario: Subtask without AI action
- **WHEN** a subtask has null action fields
- **THEN** no action button appears next to the subtask — it displays as a simple checklist item

#### Scenario: Click subtask action button
- **WHEN** a user clicks the action button on a subtask titled "Draft rental agreement" with prompt "Generate a rental agreement draft"
- **THEN** the message "Help me with subtask: Draft rental agreement -- Generate a rental agreement draft" is sent to the task chat and the view scrolls to the chat section

#### Scenario: Action loading after subtask creation
- **WHEN** a user creates a new subtask "Research visa requirements"
- **THEN** a loading spinner appears on the action button position while the action generation endpoint is called, and once complete, either an action button appears or the loading indicator disappears (if non-automatable)

## ADDED Requirements

### Requirement: Quick-Reply Buttons in Chat
The system SHALL detect quick-reply options in AI chat responses and render them as clickable buttons below the AI message. When the AI determines it needs clarification before executing a subtask action, it SHALL include quick-reply options in a structured format within its response. Each quick-reply button SHALL display a short label. Clicking a quick-reply button SHALL send the button's value as the next chat message. Quick-reply buttons SHALL disappear after one is clicked (single-use). The system SHALL detect quick-replies via a JSON block with key `quick_replies` containing an array of objects with `label` (display text) and `value` (text to send as message).

#### Scenario: AI asks clarifying question with quick-replies
- **WHEN** the AI responds to a subtask action prompt and needs clarification (e.g., "What tone should the agreement have?")
- **THEN** the AI message includes quick-reply buttons like "Formal", "Informal", "Neutral" below the text

#### Scenario: User clicks a quick-reply button
- **WHEN** a user clicks the "Formal" quick-reply button
- **THEN** "Formal" is sent as the next chat message and the quick-reply buttons disappear from that message

#### Scenario: AI does not need clarification
- **WHEN** the AI receives a straightforward subtask action prompt (e.g., "Research visa requirements for Portugal")
- **THEN** the AI executes the task directly without showing quick-reply buttons
