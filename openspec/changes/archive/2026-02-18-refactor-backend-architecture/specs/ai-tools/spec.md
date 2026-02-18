## MODIFIED Requirements

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
