# board-management Specification

## Purpose
Backend board data model, persistence, and CRUD API. Manages boards (one per goal), tasks with status and dependency tracking, task dependency edges (DAG structure), subtasks with fractional index ordering, and the AI board generation orchestration endpoint.
## Requirements
### Requirement: Board Data Model
The system SHALL store boards as database records with the following fields: `id` (UUID primary key), `goal_id` (FK to Goal, unique), `title` (string), `created_at`, and `updated_at`. Each goal SHALL have at most one board (one-to-one relationship enforced by the unique constraint on `goal_id`).

#### Scenario: Board record created during generation
- **WHEN** the AI successfully generates a board for a goal
- **THEN** a Board record is created with `goal_id` set to the goal's ID, `title` set to the AI-generated board title, and timestamps set to the current time

#### Scenario: One board per goal enforced
- **WHEN** a board already exists for a goal
- **AND** a second board creation is attempted for the same goal
- **THEN** the system SHALL reject the creation with a conflict error

### Requirement: Task Data Model
The system SHALL store tasks as database records with the following fields: `id` (UUID primary key), `board_id` (FK to Board), `title` (string), `description` (string), `status` (string enum: `not_started` / `in_progress` / `done`, default `not_started`), `is_goal_node` (boolean, default false), `due_date` (date, nullable), `priority` (string enum: `low` / `medium` / `high`, nullable), `estimated_minutes` (integer, nullable), `created_at`, and `updated_at`. Tasks SHALL be returned ordered by `created_at` ascending within their board. The progressive metadata fields (`due_date`, `priority`, `estimated_minutes`) SHALL be nullable — the AI populates them per-task only when relevant to the goal type and specific task. Exactly one task per board MUST have `is_goal_node: true` — this is the final goal completion task that serves as the single sink of the DAG.

#### Scenario: Task created with status not_started
- **WHEN** the AI generates a task during board generation
- **THEN** the task record has `status` set to `not_started` and `board_id` set to the board's ID

#### Scenario: Goal node task created
- **WHEN** the AI generates the final goal node task
- **THEN** the task record has `is_goal_node` set to `true` and depends on all leaf tasks in the board

#### Scenario: Exactly one goal node per board
- **WHEN** a board is generated
- **THEN** exactly one task in the board has `is_goal_node: true`

#### Scenario: Task created with full progressive metadata
- **WHEN** the AI generates a "Book flight to Lisbon" task for a relocation goal
- **THEN** the task record MAY include `due_date`, `priority: "high"`, and `estimated_minutes: 30`

#### Scenario: Task created without progressive metadata
- **WHEN** the AI generates a "Brainstorm potential neighborhoods" task
- **THEN** the task record MAY have `due_date`, `priority`, and `estimated_minutes` all set to null

### Requirement: Board Persistence Service
The system SHALL implement a board persistence service that supports two-phase persistence for the streaming generation flow. **Phase 1 (Skeleton persistence):** After the AI generates the board skeleton, the service SHALL create Board and Task records (with titles but empty descriptions) and TaskDependency records in a single database transaction. The service SHALL validate that the dependency graph forms a valid DAG (no cycles) before persisting. The service SHALL return a mapping of AI task IDs to database UUIDs. **Phase 2 (Enrichment persistence):** As each task enrichment completes, the service SHALL update the corresponding Task record with the description and progressive metadata, and create Subtask records for the generated subtasks, each in its own transaction. The service SHALL be located in `app/domains/boards/service.py`.

#### Scenario: Successful skeleton persistence
- **WHEN** the AI generates a skeleton with 15 tasks and 20 dependency edges
- **THEN** 1 Board record, 15 Task records (with titles, empty descriptions), and 20 TaskDependency records are created in a single transaction

#### Scenario: Persistence rollback on skeleton failure
- **WHEN** a database error occurs while creating the 10th task during skeleton persistence
- **THEN** no Board, Task, or TaskDependency records are persisted (full rollback)

#### Scenario: Cycle detection rejects invalid skeleton
- **WHEN** the AI skeleton output contains a dependency cycle (A depends on B, B depends on A)
- **THEN** the system SHALL reject the skeleton and raise an error

#### Scenario: Successful enrichment persistence
- **WHEN** enrichment completes for a task with description, priority "high", and 3 subtasks
- **THEN** the Task record is updated with the description and priority, and 3 Subtask records are created with fractional index positions

#### Scenario: Enrichment persistence independent per task
- **WHEN** enrichment persistence fails for one task
- **THEN** other tasks' enrichment persistence is not affected

### Requirement: Generate Board Endpoint
The system SHALL expose `POST /api/goals/:id/generate-board` as an authenticated SSE (Server-Sent Events) streaming endpoint. The endpoint SHALL return `Content-Type: text/event-stream`. The endpoint SHALL validate that the goal exists, belongs to the authenticated user, is in `answered` status, and does not already have a board. It SHALL then trigger the two-step AI board generation pipeline (skeleton + parallel enrichment), streaming progress events to the client as generation proceeds. The endpoint SHALL extract `user_meta` from `Goal.ai_context` and pass it to the AI generation pipeline for inclusion in prompts. The endpoint SHALL emit the following SSE events: (1) `skeleton_ready` — emitted after the skeleton is generated and Board/Task records are persisted, containing the board structure with task IDs, titles, dependency edges, and goal node flag; (2) `task_enriched` — emitted once per task as each parallel enrichment completes and the task record is updated, containing the task's description, metadata, and subtasks; (3) `generation_complete` — emitted after all enrichment completes, containing the board ID and a list of any failed task IDs; (4) `generation_error` — emitted if an unrecoverable error occurs (e.g., skeleton generation fails after all retries), containing an error message. The goal status SHALL transition to `generating` before generation starts, and to `active` after `generation_complete` is emitted. If generation fails entirely, the goal status SHALL revert to `answered`.

#### Scenario: Successful streaming board generation
- **WHEN** an authenticated user sends `POST /api/goals/:id/generate-board` for their goal in `answered` status
- **THEN** the response `Content-Type` is `text/event-stream`
- **AND** the first event is `skeleton_ready` with board structure (task IDs, titles, edges)
- **AND** subsequent events are `task_enriched` (one per task, in completion order)
- **AND** the final event is `generation_complete` with the board ID

#### Scenario: User meta passed to AI pipeline
- **WHEN** board generation is triggered for a goal with `user_meta` in `ai_context`
- **THEN** the AI generation pipeline receives the user meta for injection into skeleton and enrichment prompts

#### Scenario: Goal not in answered status
- **WHEN** a user sends `POST /api/goals/:id/generate-board` for a goal in `questioning` status
- **THEN** the response status is 409 (Conflict) with an error message indicating the goal is not ready for board generation

#### Scenario: Board already exists for goal
- **WHEN** a user sends `POST /api/goals/:id/generate-board` for a goal that already has a board
- **THEN** the response status is 409 (Conflict) with an error message indicating a board already exists

#### Scenario: User can only generate board for own goal
- **WHEN** user A sends `POST /api/goals/:id/generate-board` for user B's goal
- **THEN** the response status is 404

#### Scenario: Unauthenticated request rejected
- **WHEN** an unauthenticated user sends `POST /api/goals/:id/generate-board`
- **THEN** the response status is 401

#### Scenario: Skeleton generation failure emits error event
- **WHEN** the AI skeleton generation fails after all retry attempts
- **THEN** a `generation_error` event is emitted with an error message and the goal status reverts to `answered`

#### Scenario: Partial enrichment failure
- **WHEN** enrichment fails for 2 out of 15 tasks but succeeds for the other 13
- **THEN** 13 `task_enriched` events are emitted
- **AND** `generation_complete` includes a `failed_tasks` list with the 2 failed task IDs
- **AND** the goal status transitions to `active`

### Requirement: Get Board Endpoint
The system SHALL expose `GET /api/boards/:id` as an authenticated endpoint that returns the board with its nested tasks, subtasks, and dependency edges. Each task SHALL include its subtasks ordered by position, a list of `dependency_ids` (tasks it depends on), and a list of `dependent_ids` (tasks that depend on it). A computed `is_locked` boolean SHALL indicate whether all dependencies have status `done`. Users SHALL only be able to retrieve boards for their own goals.

#### Scenario: Retrieve board with nested data and dependencies
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a board belonging to their goal
- **THEN** the response includes the board fields, an array of tasks (each with title, description, status, `is_goal_node`, progressive metadata, nested subtasks, `dependency_ids`, `dependent_ids`, and `is_locked`), and an `edges` array of `{source, target}` pairs

#### Scenario: Retrieve another user's board
- **WHEN** user A requests `GET /api/boards/:id` for a board belonging to user B's goal
- **THEN** the response status is 404

#### Scenario: Board not found
- **WHEN** a user requests `GET /api/boards/:id` with a non-existent board ID
- **THEN** the response status is 404

### Requirement: Board Alembic Migration
The system SHALL include an Alembic migration that drops the existing `subtask`, `task`, `board_column`, and `board` tables (with all data) and recreates: `board` table (same schema), `task` table with `board_id` FK (replacing `column_id`), `status` field (varchar, default `not_started`), and no `position` field; `task_dependency` junction table with `dependent_task_id` and `dependency_task_id` FKs; and `subtask` table with `task_id` FK. Indexes SHALL exist on `board.goal_id`, `task.board_id`, `task_dependency.dependent_task_id`, `task_dependency.dependency_task_id`, and `subtask.task_id`.

#### Scenario: Migration drops old tables and creates new schema
- **WHEN** `alembic upgrade head` is run
- **THEN** the `board_column` table no longer exists
- **AND** the `task` table has `board_id` (UUID FK to board), `status` (varchar, default `not_started`), `is_goal_node` (boolean, default false), and no `column_id` or `position` columns
- **AND** the `task_dependency` table exists with `id` (UUID PK), `dependent_task_id` (UUID FK to task), `dependency_task_id` (UUID FK to task), and a unique constraint on the pair
- **AND** indexes exist on `board.goal_id`, `task.board_id`, `task_dependency.dependent_task_id`, `task_dependency.dependency_task_id`, and `subtask.task_id`

### Requirement: Subtask Data Model
The system SHALL store subtasks as database records with the following fields: `id` (UUID primary key), `task_id` (FK to Task), `title` (string), `completed` (boolean, default false), `position` (varchar(50), fractional index string for ordering), `created_at`, and `updated_at`. Subtasks SHALL be returned ordered by `position` ascending (lexicographic sort) within their parent task. Subtasks are single-level only — no nested subtasks.

#### Scenario: Subtask created for a task
- **WHEN** a user creates a subtask with title "Research visa requirements" for a task
- **THEN** a Subtask record is created with `completed` set to false and a fractional index `position`

#### Scenario: Subtask ordering within task
- **WHEN** a task has 3 subtasks with fractional index positions
- **THEN** subtasks are returned in lexicographic position order

### Requirement: List Boards Endpoint
The system SHALL expose `GET /api/boards` as an authenticated endpoint that returns all boards belonging to the authenticated user. Each board in the response SHALL include summary data: `id`, `goal_id`, `title`, `goal_title`, `task_count`, `completed_task_count` (tasks with status `done`), and `created_at`. Boards SHALL be ordered by `created_at` descending (newest first).

#### Scenario: User retrieves their boards
- **WHEN** an authenticated user with 3 boards sends `GET /api/boards`
- **THEN** the response contains 3 board summary objects ordered by creation date descending

#### Scenario: User with no boards gets empty list
- **WHEN** an authenticated user with no boards sends `GET /api/boards`
- **THEN** the response contains an empty array

#### Scenario: Board list includes progress data
- **WHEN** a board has 12 tasks total, with 3 tasks having status `done`
- **THEN** the board summary shows `task_count: 12` and `completed_task_count: 3`

#### Scenario: Unauthenticated request rejected
- **WHEN** an unauthenticated user sends `GET /api/boards`
- **THEN** the response status is 401

### Requirement: Update Board Endpoint
The system SHALL expose `PATCH /api/boards/:id` as an authenticated endpoint that updates the board title. The endpoint SHALL validate that the board belongs to the authenticated user's goal.

#### Scenario: Update board title
- **WHEN** an authenticated user sends `PATCH /api/boards/:id` with `{"title": "New Title"}`
- **THEN** the board title is updated and the response contains the updated board

#### Scenario: Update another user's board rejected
- **WHEN** user A sends `PATCH /api/boards/:id` for user B's board
- **THEN** the response status is 404

### Requirement: Create Task Endpoint
The system SHALL expose `POST /api/boards/:id/tasks` as an authenticated endpoint that creates a new task on the specified board. The request body SHALL include `title` and optionally `description`, `due_date`, `priority`, and `estimated_minutes`. The new task SHALL have `status` set to `not_started`. The endpoint SHALL validate ownership by tracing board to goal to user.

#### Scenario: Create task on board
- **WHEN** an authenticated user sends `POST /api/boards/:id/tasks` with `{"title": "Research flights"}`
- **THEN** a new task is created with the given title, status `not_started`, and the response status is 201

#### Scenario: Create task with metadata
- **WHEN** a user creates a task with `{"title": "Book hotel", "priority": "high", "due_date": "2026-03-15"}`
- **THEN** the task is created with the specified metadata fields populated

### Requirement: Update Task Endpoint
The system SHALL expose `PATCH /api/tasks/:id` as an authenticated endpoint that updates any combination of task fields: `title`, `description`, `due_date`, `priority`, `estimated_minutes`, and `status`. The endpoint SHALL validate ownership by tracing task to board to goal to user. Status transitions SHALL be validated: a task can only move to `in_progress` if all its dependencies have status `done`; a task can only move to `done` if it is currently `in_progress`.

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

#### Scenario: Update task on another user's board rejected
- **WHEN** user A sends `PATCH /api/tasks/:id` for a task on user B's board
- **THEN** the response status is 404

### Requirement: Delete Task Endpoint
The system SHALL expose `DELETE /api/tasks/:id` as an authenticated endpoint that deletes a task, all its subtasks, and all dependency edges involving the task (both as dependent and as dependency). The endpoint SHALL validate ownership by tracing task to board to goal to user.

#### Scenario: Delete task
- **WHEN** an authenticated user sends `DELETE /api/tasks/:id`
- **THEN** the task, all its subtasks, and all associated dependency edges are deleted and the response status is 204

#### Scenario: Delete task unlocks dependents
- **WHEN** task B depends only on task A and task A is deleted
- **THEN** task B has no remaining dependencies and is no longer locked

#### Scenario: Delete task on another user's board rejected
- **WHEN** user A sends `DELETE /api/tasks/:id` for a task on user B's board
- **THEN** the response status is 404

### Requirement: Create Subtask Endpoint
The system SHALL expose `POST /api/tasks/:id/subtasks` as an authenticated endpoint that creates a new subtask for the specified task. The request body SHALL include `title`. The new subtask SHALL be assigned a fractional index position after the last existing subtask. The endpoint SHALL validate ownership by tracing task to board to goal to user.

#### Scenario: Create subtask
- **WHEN** an authenticated user sends `POST /api/tasks/:id/subtasks` with `{"title": "Check visa requirements"}`
- **THEN** a new subtask is created with `completed: false` and a position after existing subtasks
- **AND** the response status is 201

### Requirement: Update Subtask Endpoint
The system SHALL expose `PATCH /api/subtasks/:id` as an authenticated endpoint that updates a subtask's `title`, `completed`, and/or `position` fields. The endpoint SHALL validate ownership by tracing subtask to task to board to goal to user.

#### Scenario: Toggle subtask completed
- **WHEN** a user sends `PATCH /api/subtasks/:id` with `{"completed": true}`
- **THEN** the subtask `completed` field is set to true

#### Scenario: Rename subtask
- **WHEN** a user sends `PATCH /api/subtasks/:id` with `{"title": "Updated subtask title"}`
- **THEN** the subtask title is updated

### Requirement: Delete Subtask Endpoint
The system SHALL expose `DELETE /api/subtasks/:id` as an authenticated endpoint that deletes a subtask. The endpoint SHALL validate ownership by tracing subtask to task to board to goal to user.

#### Scenario: Delete subtask
- **WHEN** an authenticated user sends `DELETE /api/subtasks/:id`
- **THEN** the subtask is deleted and the response status is 204

### Requirement: Task Dependency Data Model
The system SHALL store task dependencies as records in a `task_dependency` junction table with the following fields: `id` (UUID primary key), `dependent_task_id` (FK to Task — the task that is blocked), `dependency_task_id` (FK to Task — the prerequisite task), `created_at`. A unique constraint SHALL exist on the pair (`dependent_task_id`, `dependency_task_id`) to prevent duplicate edges. Both tasks in a dependency MUST belong to the same board. The dependency graph MUST form a valid DAG (no cycles).

#### Scenario: Dependency created between two tasks
- **WHEN** the AI generates task A and task B where B depends on A
- **THEN** a TaskDependency record is created with `dependency_task_id` = A and `dependent_task_id` = B

#### Scenario: Duplicate dependency rejected
- **WHEN** a dependency edge from A to B already exists and a second identical edge is attempted
- **THEN** the system SHALL reject the creation with a conflict error

#### Scenario: Cross-board dependency rejected
- **WHEN** a dependency is attempted between tasks on different boards
- **THEN** the system SHALL reject the creation with a validation error

### Requirement: Task Lock Status Computation
The system SHALL compute a `is_locked` boolean for each task based on its dependencies. A task is locked (`is_locked: true`) when at least one of its dependency tasks does NOT have status `done`. A task with no dependencies is never locked. The lock status SHALL be computed at query time and included in the API response, not stored in the database.

#### Scenario: Task with all dependencies done is unlocked
- **WHEN** task C depends on tasks A and B, and both A and B have status `done`
- **THEN** `is_locked` for task C is `false`

#### Scenario: Task with incomplete dependency is locked
- **WHEN** task C depends on tasks A and B, A has status `done` but B has status `in_progress`
- **THEN** `is_locked` for task C is `true`

#### Scenario: Task with no dependencies is unlocked
- **WHEN** task A has no dependencies
- **THEN** `is_locked` for task A is `false`

### Requirement: Board User Meta in API Response
The system SHALL include an optional `user_meta` field in the `BoardResponse` API schema. The `user_meta` value SHALL be read from the related goal's `ai_context["user_meta"]` at query time (not stored on the Board model). When the related goal has `user_meta` in its `ai_context`, the `BoardResponse` SHALL include the `user_meta` object with `timezone`, `locale`, `current_datetime`, `location` (nullable, with optional `city` and `country`), and `device_type`. When the goal has no `user_meta`, the field SHALL be null.

#### Scenario: Board response includes user_meta from goal
- **WHEN** a user retrieves a board via `GET /api/boards/:id`
- **AND** the related goal has `user_meta` in `ai_context`
- **THEN** the response includes `user_meta` with timezone, locale, current_datetime, location, and device_type

#### Scenario: Board response has null user_meta for legacy goals
- **WHEN** a user retrieves a board via `GET /api/boards/:id`
- **AND** the related goal has no `user_meta` in `ai_context`
- **THEN** the response includes `user_meta` as null

### Requirement: Board Meta Frontend Display
The system SHALL display the board's meta context on the board detail page when `user_meta` is present in the board response. The display SHALL include the generation date (formatted from `current_datetime`) and location (city, country) if available. The display SHALL be a non-intrusive informational element (e.g., a small text line or tooltip). When `user_meta` is null, no meta section SHALL be displayed.

#### Scenario: Meta displayed on board with location
- **WHEN** a user views a board detail page for a board whose response has `user_meta.location = { city: "Berlin", country: "Germany" }` and `user_meta.current_datetime = "2026-02-17T14:30:00Z"`
- **THEN** the page displays generation context such as "Generated on Feb 17, 2026 | Berlin, Germany"

#### Scenario: Meta displayed on board without location
- **WHEN** a user views a board detail page for a board whose response has `user_meta.location = null` and `user_meta.current_datetime = "2026-02-17T14:30:00Z"`
- **THEN** the page displays generation context such as "Generated on Feb 17, 2026" without location

#### Scenario: No meta section for legacy boards
- **WHEN** a user views a board detail page for a board whose response has `user_meta = null`
- **THEN** no meta information section is displayed

