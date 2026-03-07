## MODIFIED Requirements

### Requirement: Get Board Endpoint
The system SHALL expose `GET /api/boards/:id` as an authenticated endpoint that returns the board with its nested tasks, subtasks, and dependency edges. Each task SHALL include its subtasks ordered by position, a list of `dependency_ids` (tasks it depends on), and a list of `dependent_ids` (tasks that depend on it). A computed `is_locked` boolean SHALL indicate whether all dependencies have status `done`. Each task SHALL include a `sub_board_id` field (nullable string) — set to the ID of the task's sub-board if one exists, null otherwise. Each task SHALL include `sub_board_progress` (nullable object with `task_count` and `completed_task_count`) when a sub-board exists. The board response SHALL include `parent_task_id` (nullable string) and `parent_board` (nullable object with `id` and `title`) for breadcrumb navigation. Users SHALL be able to retrieve boards they own (via goal.user_id) OR boards for goals where they are a member (via goal_member). The board response SHALL include `user_role` (string: `owner`, `editor`, or `viewer`) indicating the authenticated user's permission level for the board.

#### Scenario: Retrieve board with nested data and dependencies
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a board belonging to their goal
- **THEN** the response includes the board fields, an array of tasks (each with title, description, status, `is_goal_node`, progressive metadata, nested subtasks, `dependency_ids`, `dependent_ids`, `is_locked`, `sub_board_id`, `sub_board_progress`), an `edges` array of `{source, target}` pairs, and `user_role` set to `owner`

#### Scenario: Retrieve sub-board with parent breadcrumb
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a sub-board
- **THEN** the response includes `parent_task_id` set to the parent task's ID and `parent_board` with the parent board's `id` and `title`

#### Scenario: Root board has null parent fields
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a root board
- **THEN** the response includes `parent_task_id: null` and `parent_board: null`

#### Scenario: Task with sub-board includes sub-board data
- **WHEN** a board has a task that has a sub-board with 8 tasks (3 done)
- **THEN** that task's response includes `sub_board_id` set to the sub-board's ID and `sub_board_progress: { task_count: 8, completed_task_count: 3 }`

#### Scenario: Task without sub-board has null sub-board fields
- **WHEN** a board has a task without a sub-board
- **THEN** that task's response includes `sub_board_id: null` and `sub_board_progress: null`

#### Scenario: Member retrieves shared board
- **WHEN** a goal member requests `GET /api/boards/:id` for a board belonging to a goal they are a member of
- **THEN** the response is returned with `user_role` set to the member's role (`viewer` or `editor`)

#### Scenario: Retrieve another user's board (not shared)
- **WHEN** user A requests `GET /api/boards/:id` for a board belonging to user B's goal (and A is not a member)
- **THEN** the response status is 404

#### Scenario: Board not found
- **WHEN** a user requests `GET /api/boards/:id` with a non-existent board ID
- **THEN** the response status is 404

### Requirement: List Boards Endpoint
The system SHALL expose `GET /api/boards` as an authenticated endpoint that returns all root-level boards accessible to the authenticated user. This includes boards owned by the user (goal.user_id matches) AND boards for goals where the user is a member (via goal_member). Only boards with `parent_task_id IS NULL` SHALL be returned (sub-boards are excluded). Each board in the response SHALL include summary data: `id`, `goal_id`, `title`, `goal_title`, `task_count`, `completed_task_count` (tasks with status `done`), `created_at`, and `user_role` (string: `owner`, `editor`, or `viewer`). Boards SHALL be ordered by `created_at` descending (newest first). An optional `filter` query parameter SHALL support values `owned`, `shared`, or `all` (default: `all`).

#### Scenario: User retrieves all accessible boards
- **WHEN** an authenticated user with 3 owned boards, 2 shared boards, and 2 sub-boards sends `GET /api/boards`
- **THEN** the response contains 5 board summary objects ordered by creation date descending (sub-boards excluded), each with `user_role`

#### Scenario: User filters to owned boards only
- **WHEN** a user sends `GET /api/boards?filter=owned`
- **THEN** only boards where `user_role` is `owner` are returned

#### Scenario: User filters to shared boards only
- **WHEN** a user sends `GET /api/boards?filter=shared`
- **THEN** only boards where `user_role` is `viewer` or `editor` are returned

#### Scenario: User with no boards gets empty list
- **WHEN** an authenticated user with no owned or shared boards sends `GET /api/boards`
- **THEN** the response contains an empty array

#### Scenario: Board list includes progress data
- **WHEN** a board has 12 tasks total, with 3 tasks having status `done`
- **THEN** the board summary shows `task_count: 12` and `completed_task_count: 3`

#### Scenario: Unauthenticated request rejected
- **WHEN** an unauthenticated user sends `GET /api/boards`
- **THEN** the response status is 401

### Requirement: Update Task Endpoint
The system SHALL expose `PATCH /api/tasks/:id` as an authenticated endpoint that updates any combination of task fields: `title`, `description`, `due_date`, `priority`, `estimated_minutes`, and `status`. The endpoint SHALL validate ownership by tracing task to board to goal to user, or verify the user is a goal member with `editor` role. Users with `viewer` role SHALL NOT be able to update tasks. Status transitions SHALL be validated: a task can only move to `in_progress` if all its dependencies have status `done`; a task can only move to `done` if it is currently `in_progress`.

#### Scenario: Update task title
- **WHEN** an authenticated user sends `PATCH /api/tasks/:id` with `{"title": "Updated title"}`
- **THEN** the task title is updated

#### Scenario: Start task with met dependencies
- **WHEN** a task has 2 dependencies both with status `done` and a user sends `PATCH /api/tasks/:id` with `{"status": "in_progress"}`
- **THEN** the task status is updated to `in_progress`

#### Scenario: Start task with unmet dependencies rejected
- **WHEN** a task has a dependency with status `not_started` and a user sends `PATCH /api/tasks/:id` with `{"status": "in_progress"}`
- **THEN** the response status is 409 (Conflict) with an error indicating unmet dependencies

#### Scenario: Complete task that is in progress
- **WHEN** a task has status `in_progress` and a user sends `PATCH /api/tasks/:id` with `{"status": "done"}`
- **THEN** the task status is updated to `done`

#### Scenario: Complete task that is not started rejected
- **WHEN** a task has status `not_started` and a user sends `PATCH /api/tasks/:id` with `{"status": "done"}`
- **THEN** the response status is 409 (Conflict) with an error indicating the task must be in progress first

#### Scenario: Editor member updates task on shared board
- **WHEN** a goal member with `editor` role sends `PATCH /api/tasks/:id` for a task on a shared board
- **THEN** the task is updated successfully

#### Scenario: Viewer member cannot update task
- **WHEN** a goal member with `viewer` role sends `PATCH /api/tasks/:id` for a task on a shared board
- **THEN** the response status is 403 (Forbidden)

#### Scenario: Update task on another user's board rejected
- **WHEN** user A sends `PATCH /api/tasks/:id` for a task on user B's board (and A is not a member)
- **THEN** the response status is 404
