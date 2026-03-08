## 1. Backend: Background action generation function

- [x] 1.1 Create `generate_board_subtask_actions(session, board_id, user_id)` async function in `backend/app/domains/templates/service.py` (or a shared utility module). The function loads all tasks with subtasks for the board, resolves `user_context` from the goal's `ai_context.user_meta`, and calls `generate_subtask_actions` per task in parallel via `asyncio.gather(return_exceptions=True)`. For each successful result, match actions to subtasks by title and batch-update `action_label`, `action_icon`, `action_prompt` fields. Log and skip failures per task.

- [x] 1.2 Add a helper in `subtask_repository.py` (or inline) to batch-update action fields on multiple subtasks in a single DB round-trip.

## 2. Backend: Wire up background generation in template endpoints

- [x] 2.1 In `create_board_from_template` (templates/service.py), after the board is created and committed, call `generate_board_subtask_actions` as a background task (using `asyncio.ensure_future` or FastAPI `BackgroundTasks`). The board creation response MUST return before action generation starts.

- [x] 2.2 In the `save-generated` router (templates/router.py), when `create_board=True`, ensure the same background action generation is triggered after the board is created (this already goes through `create_board_from_template`, so 2.1 may cover it — verify and adjust if the background task needs to be wired at the router level instead).

## 3. Testing

- [x] 3.1 Write an integration test: create a board from a template that has subtasks, mock `generate_subtask_actions` to return known actions, verify subtask action fields are populated after the background task completes.

- [x] 3.2 Write a test for graceful degradation: mock `generate_subtask_actions` to raise an exception for one task, verify other tasks' subtasks still get actions and the board is intact.

- [x] 3.3 Write a test for the `save-generated` + `create_board=True` path: verify background action generation is triggered.

## 4. Validation

- [x] 4.1 Manual test: create a board from a template with multiple tasks and subtasks, confirm action buttons appear on subtasks after a brief delay.

- [x] 4.2 Run existing test suite to confirm no regressions.
