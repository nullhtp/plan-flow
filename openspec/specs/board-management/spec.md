# board-management Specification

## Purpose
Backend board data model, persistence, and CRUD API. Manages boards (one per goal), tasks with status and dependency tracking, task dependency edges (DAG structure), subtasks with fractional index ordering, and the AI board generation orchestration endpoint.
## Requirements
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
The system SHALL implement board persistence as a set of focused service modules split by entity. **Board operations** (`app/domains/boards/board_service.py`): board CRUD, board listing with summary data, and board response building. **Task operations** (`app/domains/boards/task_service.py`): task CRUD, status transition validation, dependency query helpers, and board generation orchestration (consuming AI stream, persisting skeleton, running enrichment, managing goal state transitions via `goals/service.py`). **Subtask operations** (`app/domains/boards/subtask_service.py`): subtask CRUD with fractional index positioning. Fractional indexing utilities SHALL be extracted to `app/domains/boards/position_utils.py`. Ownership validation SHALL be extracted to `app/domains/boards/ownership.py` and shared across boards and AI domains. All services SHALL use repository classes for database access instead of direct SQLAlchemy session calls. **Phase 1 (Skeleton persistence):** After the AI generates the board skeleton, the task service SHALL create Board and Task records (with titles but empty descriptions) and TaskDependency records in a single database transaction. The service SHALL validate that the dependency graph forms a valid DAG (no cycles) before persisting. The service SHALL return a mapping of AI task IDs to database UUIDs. **Phase 2 (Enrichment persistence):** As each task enrichment completes, the task service SHALL update the corresponding Task record with the description and progressive metadata, and create Subtask records for the generated subtasks, each in its own transaction.

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

#### Scenario: Ownership validation shared across domains
- **WHEN** the AI domain needs to validate board ownership for a chat endpoint
- **THEN** it imports and calls the shared ownership validation from `app/domains/boards/ownership.py`

### Requirement: Generate Board Endpoint
The system SHALL expose `POST /api/goals/:id/generate-board` as an authenticated SSE (Server-Sent Events) streaming endpoint. The endpoint router SHALL be a thin HTTP layer that delegates all business orchestration to `task_service.generate_board()`. The service function SHALL validate that the goal exists, belongs to the authenticated user, is in `answered` status, and does not already have a board. It SHALL transition the goal status to `generating` by calling `goals/service.py`, trigger the two-step AI board generation pipeline (skeleton + parallel enrichment), stream progress events to the client, extract `user_meta` from `Goal.ai_context` and pass it to the AI generation pipeline, and transition the goal status to `active` after completion. If generation fails entirely, the goal status SHALL revert to `answered` via `goals/service.py`. The endpoint SHALL emit the following SSE events: (1) `skeleton_ready`, (2) `task_enriched`, (3) `generation_complete`, (4) `generation_error`.

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

### Requirement: Board Alembic Migration
The system SHALL include an Alembic migration that drops the existing `subtask`, `task`, `board_column`, and `board` tables (with all data) and recreates: `board` table (same schema), `task` table with `board_id` FK (replacing `column_id`), `status` field (varchar, default `not_started`), and no `position` field; `task_dependency` junction table with `dependent_task_id` and `dependency_task_id` FKs; and `subtask` table with `task_id` FK. Indexes SHALL exist on `board.goal_id`, `task.board_id`, `task_dependency.dependent_task_id`, `task_dependency.dependency_task_id`, and `subtask.task_id`.

#### Scenario: Migration drops old tables and creates new schema
- **WHEN** `alembic upgrade head` is run
- **THEN** the `board_column` table no longer exists
- **AND** the `task` table has `board_id` (UUID FK to board), `status` (varchar, default `not_started`), `is_goal_node` (boolean, default false), and no `column_id` or `position` columns
- **AND** the `task_dependency` table exists with `id` (UUID PK), `dependent_task_id` (UUID FK to task), `dependency_task_id` (UUID FK to task), and a unique constraint on the pair
- **AND** indexes exist on `board.goal_id`, `task.board_id`, `task_dependency.dependent_task_id`, `task_dependency.dependency_task_id`, and `subtask.task_id`

### Requirement: Subtask Data Model
The system SHALL store subtasks as database records with the following fields: `id` (UUID primary key), `task_id` (FK to Task), `title` (string), `completed` (boolean, default false), `position` (varchar(50), fractional index string for ordering), `action_label` (varchar(60), nullable, short button text for AI action), `action_icon` (varchar(20), nullable, semantic icon category), `action_prompt` (text, nullable, max 500 chars, prompt to send to task chat), `created_at`, and `updated_at`. Subtasks SHALL be returned ordered by `position` ascending (lexicographic sort) within their parent task. Subtasks are single-level only — no nested subtasks. The action fields (`action_label`, `action_icon`, `action_prompt`) represent an optional AI-generated action button for the subtask. When all three are null, the subtask has no AI action available.

#### Scenario: Subtask created for a task
- **WHEN** a user creates a subtask with title "Research visa requirements" for a task
- **THEN** a Subtask record is created with `completed` set to false, a fractional index `position`, and null action fields

#### Scenario: Subtask ordering within task
- **WHEN** a task has 3 subtasks with fractional index positions
- **THEN** subtasks are returned in lexicographic position order

#### Scenario: Subtask with AI action
- **WHEN** the enrichment pipeline generates a subtask "Draft rental agreement" with an AI action
- **THEN** the Subtask record has `action_label: "Generate agreement draft"`, `action_icon: "generate"`, `action_prompt: "Generate a rental agreement draft based on the task context"`

#### Scenario: Subtask without AI action
- **WHEN** the enrichment pipeline generates a subtask "Sign documents at notary"
- **THEN** the Subtask record has `action_label: null`, `action_icon: null`, `action_prompt: null`

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

### Requirement: Pending Action Alembic Migration
The system SHALL include an Alembic migration that creates the `pending_action` table with columns: `id` (UUID PK), `user_id` (UUID FK to user), `thread_id` (varchar, indexed), `tool_name` (varchar), `tool_args` (JSON), `description` (varchar), `status` (varchar, default `pending`), `result` (JSON, nullable), `created_at` (timestamptz), `expires_at` (timestamptz). Indexes SHALL exist on `user_id`, `thread_id`, and `(thread_id, status)` for efficient lookups.

#### Scenario: Migration creates pending_action table
- **WHEN** `alembic upgrade head` is run
- **THEN** the `pending_action` table exists with all specified columns, foreign keys, and indexes

### Requirement: Board Chat Endpoint in Router
The system SHALL mount the `POST /api/boards/{board_id}/chat` endpoint in the AI router alongside the existing task chat endpoint. The endpoint SHALL follow the same authentication and ownership validation pattern as existing board endpoints (trace board to goal to user). The endpoint SHALL be tagged with `ai` in the OpenAPI spec.

#### Scenario: Board chat endpoint accessible
- **WHEN** an authenticated user sends POST /api/boards/{board_id}/chat
- **THEN** the request is routed to the board chat handler

#### Scenario: Board chat endpoint in OpenAPI spec
- **WHEN** the OpenAPI spec is generated
- **THEN** the board chat endpoint appears under the `ai` tag with request/response schemas documented

### Requirement: Artifact Data Model and Migration
The system SHALL define an `Artifact` SQLModel in `app/domains/boards/models.py` with fields: `id` (UUID string, primary key, default uuid4), `task_id` (UUID string, foreign key to `task.id`, on-delete cascade), `title` (str, max 200), `content` (text), `content_type` (str, default "text/markdown"), `created_by` (str, one of "ai" | "user"), `created_at` (datetime, server default), `updated_at` (datetime, server default, on-update). The model SHALL have an index on `task_id`. An Alembic migration SHALL create the `artifact` table.

#### Scenario: Artifact table created by migration
- **WHEN** the Alembic migration runs
- **THEN** the `artifact` table exists with all columns, the foreign key to `task` with cascade delete, and an index on `task_id`

### Requirement: Artifact Repository
The system SHALL define an `ArtifactRepository` in `app/domains/boards/artifact_repository.py` with methods: `create(db, task_id, title, content, content_type, created_by) -> Artifact`, `list_by_task(db, task_id) -> list[Artifact]` (ordered by created_at desc), `get_by_id(db, artifact_id) -> Artifact | None`, `delete(db, artifact_id) -> None`, `count_by_task(db, task_id) -> int`.

#### Scenario: List artifacts for a task ordered by newest first
- **WHEN** `list_by_task` is called for a task with 3 artifacts
- **THEN** the 3 artifacts are returned ordered by `created_at` descending

#### Scenario: Count artifacts for a task
- **WHEN** `count_by_task` is called for a task with 2 artifacts
- **THEN** the method returns 2

### Requirement: Artifact Service
The system SHALL define artifact service functions in `app/domains/boards/artifact_service.py` with methods: `create_artifact(db, task_id, title, content, content_type, created_by) -> Artifact`, `list_artifacts(db, task_id) -> list[Artifact]`, `get_artifact(db, artifact_id) -> Artifact`, `delete_artifact(db, artifact_id) -> None`. The service SHALL use `ArtifactRepository` for data access.

#### Scenario: Create artifact via service
- **WHEN** `create_artifact` is called with valid task_id and content
- **THEN** an Artifact record is created and returned

### Requirement: Artifact CRUD Router
The system SHALL provide artifact CRUD endpoints in the boards router: `GET /api/tasks/{task_id}/artifacts` (list), `GET /api/tasks/{task_id}/artifacts/{artifact_id}` (get), `DELETE /api/tasks/{task_id}/artifacts/{artifact_id}` (delete). All endpoints SHALL validate task ownership via the existing ownership utility. The router SHALL be mounted alongside existing task endpoints.

#### Scenario: List artifacts endpoint
- **WHEN** `GET /api/tasks/{task_id}/artifacts` is called by the task owner
- **THEN** the endpoint returns the list of artifacts for that task

#### Scenario: Delete artifact by non-owner
- **WHEN** `DELETE /api/tasks/{task_id}/artifacts/{artifact_id}` is called by a user who does not own the task
- **THEN** the endpoint returns 403 Forbidden

### Requirement: Action Suggestion Router
The system SHALL provide a `POST /api/tasks/{task_id}/actions/suggest` endpoint in the AI router. The endpoint SHALL validate task ownership, build the task context string (title, description, status, subtasks, immediate dependencies and dependents), call `generate_action_suggestions`, and return `ActionSuggestionsResponse`. The endpoint SHALL be mounted alongside the existing task chat endpoint.

#### Scenario: Action suggestions returned for owned task
- **WHEN** `POST /api/tasks/{task_id}/actions/suggest` is called by the task owner
- **THEN** the endpoint returns 2–4 action suggestions

#### Scenario: Action suggestions for non-owned task
- **WHEN** `POST /api/tasks/{task_id}/actions/suggest` is called by a non-owner
- **THEN** the endpoint returns 403 Forbidden

### Requirement: Subtask Action Fields Migration
The system SHALL include an Alembic migration that adds three nullable columns to the `subtask` table: `action_label` (varchar(60)), `action_icon` (varchar(20)), and `action_prompt` (text). The migration SHALL be non-destructive — existing subtask records retain their current data with null action fields.

#### Scenario: Migration adds action columns
- **WHEN** the Alembic migration runs
- **THEN** the `subtask` table has new nullable columns `action_label`, `action_icon`, and `action_prompt`
- **AND** existing subtask records have null values for all three new columns

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

### Requirement: Board Creation from Template
The system SHALL support creating a board from a template as an alternative to AI generation. When a board is created from a template, a Goal record SHALL be created with `status: active` (skipping the questioning and generation flow), `ai_context` containing `{"source": "template", "template_id": "<template_id>"}`, and `title` matching the template title or a user-provided override. A Board record SHALL be created linked to the goal with tasks, dependencies, and subtasks copied from the template. All tasks SHALL have `status: not_started`, all subtasks SHALL have `completed: false`. The template-created board SHALL behave identically to an AI-generated board for all subsequent operations (task updates, sub-board creation, chat, etc.). This updates the previous convention that board generation is purely dynamic — templates provide an alternative creation path.

#### Scenario: Board created from template has correct goal status
- **WHEN** a board is created from a template
- **THEN** the associated goal has `status: active` and does not go through the questioning or generating flow

#### Scenario: Template-created board supports all board operations
- **WHEN** a board is created from a template
- **THEN** the user can update tasks, create sub-boards, use task chat, and perform all operations available on AI-generated boards

#### Scenario: Template-created board has source metadata
- **WHEN** a board is created from a template with ID "abc-123"
- **THEN** the goal's `ai_context` contains `{"source": "template", "template_id": "abc-123"}`

