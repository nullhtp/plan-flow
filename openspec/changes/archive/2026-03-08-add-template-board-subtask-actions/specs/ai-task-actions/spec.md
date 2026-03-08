## ADDED Requirements

### Requirement: Background Subtask Action Generation for Template Boards
The system SHALL provide an async function `generate_board_subtask_actions(session: AsyncSession, board_id: str, user_id: str)` in the templates service layer (or a shared utility) that generates AI actions for all subtasks on a newly created board. The function SHALL: (1) load all tasks with their subtasks for the given board, (2) for each task that has subtasks, call `generate_subtask_actions` with the task's title, description, status, and subtask list, (3) run these calls in parallel using `asyncio.gather` with `return_exceptions=True`, (4) for each successful result, match actions to subtasks by title and update the `action_label`, `action_icon`, and `action_prompt` fields via a batch DB update, (5) resolve `user_context` from the board's goal `ai_context.user_meta` when available. The function SHALL use graceful degradation: if an LLM call fails for a particular task, that task's subtasks are skipped (no action fields set) and processing continues for other tasks. The function SHALL log errors but never raise exceptions.

#### Scenario: Actions generated for all tasks in parallel
- **WHEN** `generate_board_subtask_actions` is called for a board with 5 tasks, each having 3 subtasks
- **THEN** 5 parallel LLM calls are made (one per task)
- **AND** each subtask's `action_label`, `action_icon`, and `action_prompt` are populated based on the LLM response

#### Scenario: Partial failure does not block other tasks
- **WHEN** `generate_board_subtask_actions` is called and the LLM call for task 3 fails
- **THEN** subtasks for tasks 1, 2, 4, and 5 still receive their AI actions
- **AND** subtasks for task 3 retain null action fields
- **AND** the error is logged

#### Scenario: Tasks without subtasks are skipped
- **WHEN** a board has 3 tasks but only 2 of them have subtasks
- **THEN** only 2 LLM calls are made (tasks without subtasks are skipped)

#### Scenario: User context passed to action generation
- **WHEN** the board's goal has `ai_context.user_meta` with timezone and locale information
- **THEN** the `user_context` string is passed to `generate_subtask_actions` for each task
