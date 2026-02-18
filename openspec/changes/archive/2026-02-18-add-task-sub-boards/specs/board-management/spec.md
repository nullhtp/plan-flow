## MODIFIED Requirements

### Requirement: Board Data Model
The system SHALL store boards as database records with the following fields: `id` (UUID primary key), `goal_id` (FK to Goal, nullable, unique among non-null values), `parent_task_id` (FK to Task, nullable, unique — the task this board decomposes), `title` (string), `created_at`, and `updated_at`. A root board has `goal_id` set and `parent_task_id` null. A sub-board has `parent_task_id` set and `goal_id` null. Each goal SHALL have at most one board (one-to-one relationship enforced by the unique constraint on `goal_id` among non-null values). Each task SHALL have at most one sub-board (one-to-one relationship enforced by the unique constraint on `parent_task_id`). A sub-board's parent task MUST belong to a root-level board (nesting limited to 1 level).

#### Scenario: Board record created during generation
- **WHEN** the AI successfully generates a board for a goal
- **THEN** a Board record is created with `goal_id` set to the goal's ID, `parent_task_id` null, `title` set to the AI-generated board title, and timestamps set to the current time

#### Scenario: Sub-board record created for a task
- **WHEN** the AI successfully generates a sub-board for a task on a root board
- **THEN** a Board record is created with `parent_task_id` set to the task's ID, `goal_id` null, `title` set to the AI-generated sub-board title, and timestamps set to the current time

#### Scenario: One board per goal enforced
- **WHEN** a board already exists for a goal
- **AND** a second board creation is attempted for the same goal
- **THEN** the system SHALL reject the creation with a conflict error

#### Scenario: One sub-board per task enforced
- **WHEN** a sub-board already exists for a task
- **AND** a second sub-board creation is attempted for the same task
- **THEN** the system SHALL reject the creation with a conflict error

#### Scenario: Nested sub-board rejected
- **WHEN** a sub-board creation is attempted for a task that belongs to a sub-board (not a root board)
- **THEN** the system SHALL reject the creation with a validation error indicating sub-boards cannot be nested beyond 1 level

### Requirement: List Boards Endpoint
The system SHALL expose `GET /api/boards` as an authenticated endpoint that returns all root-level boards belonging to the authenticated user. Only boards with `parent_task_id IS NULL` SHALL be returned (sub-boards are excluded). Each board in the response SHALL include summary data: `id`, `goal_id`, `title`, `goal_title`, `task_count`, `completed_task_count` (tasks with status `done`), and `created_at`. Boards SHALL be ordered by `created_at` descending (newest first).

#### Scenario: User retrieves their boards
- **WHEN** an authenticated user with 3 root boards and 2 sub-boards sends `GET /api/boards`
- **THEN** the response contains 3 board summary objects ordered by creation date descending (sub-boards excluded)

#### Scenario: User with no boards gets empty list
- **WHEN** an authenticated user with no boards sends `GET /api/boards`
- **THEN** the response contains an empty array

#### Scenario: Board list includes progress data
- **WHEN** a board has 12 tasks total, with 3 tasks having status `done`
- **THEN** the board summary shows `task_count: 12` and `completed_task_count: 3`

#### Scenario: Unauthenticated request rejected
- **WHEN** an unauthenticated user sends `GET /api/boards`
- **THEN** the response status is 401

### Requirement: Get Board Endpoint
The system SHALL expose `GET /api/boards/:id` as an authenticated endpoint that returns the board with its nested tasks, subtasks, and dependency edges. Each task SHALL include its subtasks ordered by position, a list of `dependency_ids` (tasks it depends on), and a list of `dependent_ids` (tasks that depend on it). A computed `is_locked` boolean SHALL indicate whether all dependencies have status `done`. Each task SHALL include a `sub_board_id` field (nullable string) — set to the ID of the task's sub-board if one exists, null otherwise. Each task SHALL include `sub_board_progress` (nullable object with `task_count` and `completed_task_count`) when a sub-board exists. The board response SHALL include `parent_task_id` (nullable string) and `parent_board` (nullable object with `id` and `title`) for breadcrumb navigation. Users SHALL only be able to retrieve boards for their own goals (root boards) or boards whose parent task traces back to their own goal (sub-boards).

#### Scenario: Retrieve board with nested data and dependencies
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a board belonging to their goal
- **THEN** the response includes the board fields, an array of tasks (each with title, description, status, `is_goal_node`, progressive metadata, nested subtasks, `dependency_ids`, `dependent_ids`, `is_locked`, `sub_board_id`, `sub_board_progress`), and an `edges` array of `{source, target}` pairs

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

#### Scenario: Retrieve another user's board
- **WHEN** user A requests `GET /api/boards/:id` for a board belonging to user B's goal
- **THEN** the response status is 404

#### Scenario: Board not found
- **WHEN** a user requests `GET /api/boards/:id` with a non-existent board ID
- **THEN** the response status is 404

## ADDED Requirements

### Requirement: Sub-Board Question Generation Endpoint
The system SHALL expose `POST /api/tasks/:id/sub-board-questions` as an authenticated endpoint that generates 2-4 focused questions for decomposing the task into a sub-board. The endpoint SHALL validate that: the task exists and belongs to the authenticated user, the task belongs to a root-level board (not a sub-board), the task does not already have a sub-board. The endpoint SHALL call the AI service to generate questions using the parent task's title, description, the root board's title, and the original goal context. The response SHALL conform to a schema containing an array of questions (same format as goal questions: `id`, `text`, `type`, `options`, `rationale`, `required`). Questions SHALL have IDs prefixed with "sbq" (e.g., "sbq1").

#### Scenario: Questions generated for a task
- **WHEN** an authenticated user sends `POST /api/tasks/:id/sub-board-questions` for their task on a root board with no existing sub-board
- **THEN** the response contains 2-4 questions about how to decompose the task, with types matching the standard question format

#### Scenario: Task already has sub-board
- **WHEN** a user sends `POST /api/tasks/:id/sub-board-questions` for a task that already has a sub-board
- **THEN** the response status is 409 (Conflict) with an error indicating a sub-board already exists

#### Scenario: Task on sub-board rejected
- **WHEN** a user sends `POST /api/tasks/:id/sub-board-questions` for a task that belongs to a sub-board
- **THEN** the response status is 422 with an error indicating sub-boards cannot be nested

#### Scenario: Task not owned by user
- **WHEN** user A sends `POST /api/tasks/:id/sub-board-questions` for user B's task
- **THEN** the response status is 404

### Requirement: Sub-Board Generation Endpoint
The system SHALL expose `POST /api/tasks/:id/generate-sub-board` as an authenticated SSE streaming endpoint. The request body SHALL include `answers` (array of `{ question_id: string, value: string | string[] | number }`). The endpoint SHALL validate that: the task exists and belongs to the authenticated user, the task belongs to a root-level board, the task does not already have a sub-board, the task's dependencies are met (unlocked) or the task is already in `in_progress` status. The endpoint SHALL trigger the AI sub-board generation pipeline (skeleton + parallel enrichment). If the parent task is in `not_started` status and its dependencies are met, the endpoint SHALL auto-transition it to `in_progress`. If the parent task has existing subtasks, they SHALL be deleted before sub-board creation. The endpoint SHALL emit SSE events: (1) `skeleton_ready`, (2) `task_enriched`, (3) `generation_complete`, (4) `generation_error`.

#### Scenario: Successful sub-board generation
- **WHEN** an authenticated user sends `POST /api/tasks/:id/generate-sub-board` with answers for their unlocked task on a root board
- **THEN** the response streams SSE events: `skeleton_ready` with sub-board structure, multiple `task_enriched` events, and `generation_complete` with the sub-board ID

#### Scenario: Parent task auto-starts on sub-board generation
- **WHEN** a task has status `not_started` with all dependencies met and a sub-board is generated
- **THEN** the parent task status transitions to `in_progress`

#### Scenario: Existing subtasks deleted on sub-board creation
- **WHEN** a task has 5 subtasks and a sub-board is generated for it
- **THEN** the 5 subtasks are deleted and the sub-board is created

#### Scenario: Task already has sub-board rejected
- **WHEN** a user sends `POST /api/tasks/:id/generate-sub-board` for a task that already has a sub-board
- **THEN** the response status is 409 (Conflict)

#### Scenario: Task on sub-board rejected
- **WHEN** a user sends `POST /api/tasks/:id/generate-sub-board` for a task on a sub-board
- **THEN** the response status is 422

#### Scenario: Locked task rejected
- **WHEN** a user sends `POST /api/tasks/:id/generate-sub-board` for a locked task (dependencies not met)
- **THEN** the response status is 409 (Conflict) with an error indicating the task is locked

#### Scenario: Skeleton generation failure emits error event
- **WHEN** the AI sub-board skeleton generation fails after all retry attempts
- **THEN** a `generation_error` event is emitted with an error message

### Requirement: Sub-Board Completion Propagation
The system SHALL automatically transition a parent task to `done` when its sub-board's goal node transitions to `done`. The propagation SHALL be triggered server-side during the task status update flow. When the goal node of a sub-board is marked `done`, the system SHALL: (1) look up the sub-board's `parent_task_id`, (2) if the parent task exists and its status is not already `done`, transition the parent task to `done` (skipping the normal `in_progress` prerequisite since the sub-board proves the work is complete), (3) trigger any cascading unlock effects on the parent board (dependents of the parent task may become unlocked). The propagation SHALL NOT trigger if the parent task has already been deleted.

#### Scenario: Sub-board goal node done propagates to parent task
- **WHEN** a user marks the goal node of a sub-board as `done`
- **THEN** the parent task on the root board automatically transitions to `done`

#### Scenario: Parent task completion unlocks dependents on root board
- **WHEN** a parent task is auto-completed via sub-board propagation and task C on the root board depends only on this parent task
- **THEN** task C becomes unlocked on the root board

#### Scenario: Already-done parent task is not re-transitioned
- **WHEN** the goal node of a sub-board is marked `done` and the parent task is already `done`
- **THEN** no status change occurs on the parent task

#### Scenario: Deleted parent task does not cause error
- **WHEN** the goal node of a sub-board is marked `done` but the parent task has been deleted
- **THEN** no propagation occurs and no error is raised

### Requirement: Sub-Board Alembic Migration
The system SHALL include an Alembic migration that: (1) adds a nullable `parent_task_id` column (UUID FK to `task.id`, on-delete CASCADE) to the `board` table, (2) makes the existing `goal_id` column nullable, (3) adds a unique index on `parent_task_id` (for non-null values), (4) adds a check constraint ensuring at least one of `goal_id` or `parent_task_id` is non-null. Existing board records are unaffected (they all have `goal_id` set and `parent_task_id` null).

#### Scenario: Migration adds parent_task_id column
- **WHEN** `alembic upgrade head` is run
- **THEN** the `board` table has a nullable `parent_task_id` column with FK to `task.id` and a unique index
- **AND** the `goal_id` column is now nullable
- **AND** a check constraint ensures `goal_id IS NOT NULL OR parent_task_id IS NOT NULL`
- **AND** existing board records are unchanged

### Requirement: Delete Task Cascades to Sub-Board
The system SHALL cascade-delete a task's sub-board when the task is deleted. When a task with a sub-board is deleted via `DELETE /api/tasks/:id`, the sub-board and all its tasks, subtasks, dependency edges, and artifacts SHALL be deleted. This is enforced by the `ON DELETE CASCADE` FK from `board.parent_task_id` to `task.id`.

#### Scenario: Deleting task deletes its sub-board
- **WHEN** a user deletes a task that has a sub-board with 8 tasks
- **THEN** the task, its sub-board, and all 8 sub-board tasks (with their subtasks, edges, and artifacts) are deleted

#### Scenario: Deleting task without sub-board unchanged
- **WHEN** a user deletes a task that has no sub-board
- **THEN** only the task, its subtasks, and its dependency edges are deleted (existing behavior)
