## MODIFIED Requirements

### Requirement: Column Data Model
The system SHALL store columns as database records with the following fields: `id` (UUID primary key), `board_id` (FK to Board), `title` (string), `description` (string), `position` (varchar(50), fractional index string for ordering), `created_at`, and `updated_at`. Columns SHALL be returned ordered by `position` ascending (lexicographic sort). Position values SHALL use fractional indexing — a string-based ordering scheme where new positions can be generated between any two existing positions without modifying other records.

#### Scenario: Columns created with AI-assigned positions
- **WHEN** a board is generated with 5 columns
- **THEN** each column record has a unique fractional index `position` value and columns are retrievable in lexicographic position order

#### Scenario: Column belongs to a board
- **WHEN** a column is created
- **THEN** it MUST reference a valid board via `board_id`

#### Scenario: Column inserted between existing columns
- **WHEN** a column is inserted between two columns with positions "a0" and "a1"
- **THEN** the new column receives a position between "a0" and "a1" (e.g., "a0V") without modifying the positions of any other columns

### Requirement: Task Data Model
The system SHALL store tasks as database records with the following fields: `id` (UUID primary key), `column_id` (FK to Column), `title` (string), `description` (string), `position` (varchar(50), fractional index string for ordering), `due_date` (date, nullable), `priority` (string enum: "low"/"medium"/"high", nullable), `estimated_minutes` (integer, nullable), `created_at`, and `updated_at`. Tasks SHALL be returned ordered by `position` ascending (lexicographic sort) within their column. The progressive metadata fields (`due_date`, `priority`, `estimated_minutes`) SHALL be nullable — the AI populates them per-task only when relevant to the goal type and specific task.

#### Scenario: Task created with full progressive metadata
- **WHEN** the AI generates a "Book flight to Lisbon" task for a relocation goal
- **THEN** the task record MAY include `due_date`, `priority: "high"`, and `estimated_minutes: 30`

#### Scenario: Task created without progressive metadata
- **WHEN** the AI generates a "Brainstorm potential neighborhoods" task
- **THEN** the task record MAY have `due_date`, `priority`, and `estimated_minutes` all set to null

#### Scenario: Tasks ordered within column
- **WHEN** a column contains 4 tasks with fractional index positions
- **THEN** tasks are returned in lexicographic position order

#### Scenario: Task inserted between existing tasks
- **WHEN** a task is inserted between two tasks in the same column
- **THEN** the new task receives a fractional index position between the two neighbors without modifying any other task positions

### Requirement: Get Board Endpoint
The system SHALL expose `GET /api/boards/:id` as an authenticated endpoint that returns the board with its nested columns, tasks, and subtasks. Each column SHALL include its tasks ordered by position. Each task SHALL include its subtasks ordered by position. Columns SHALL be ordered by position. Users SHALL only be able to retrieve boards for their own goals.

#### Scenario: Retrieve board with nested data
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a board belonging to their goal
- **THEN** the response includes the board fields, an array of columns (each with title, description, position), each column includes an array of tasks (each with title, description, position, progressive metadata, and nested subtasks)

#### Scenario: Retrieve another user's board
- **WHEN** user A requests `GET /api/boards/:id` for a board belonging to user B's goal
- **THEN** the response status is 404

#### Scenario: Board not found
- **WHEN** a user requests `GET /api/boards/:id` with a non-existent board ID
- **THEN** the response status is 404

### Requirement: Board Alembic Migration
The system SHALL include Alembic migrations that create and maintain the `board`, `column`, `task`, and `subtask` tables with all required columns, foreign keys, indexes, and constraints. A migration SHALL convert existing integer `position` columns on `column` and `task` tables to varchar(50) fractional index strings. The migration SHALL add the `subtask` table. Indexes SHALL exist on `board.goal_id`, `column.board_id`, `task.column_id`, and `subtask.task_id`.

#### Scenario: Migration creates board tables and subtask table
- **WHEN** `alembic upgrade head` is run
- **THEN** the `board` table exists with columns: `id` (UUID PK), `goal_id` (UUID FK to goal, unique), `title` (varchar), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** the `column` table exists with columns: `id` (UUID PK), `board_id` (UUID FK to board), `title` (varchar), `description` (text), `position` (varchar(50)), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** the `task` table exists with columns: `id` (UUID PK), `column_id` (UUID FK to column), `title` (varchar), `description` (text), `position` (varchar(50)), `due_date` (date, nullable), `priority` (varchar, nullable), `estimated_minutes` (integer, nullable), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** the `subtask` table exists with columns: `id` (UUID PK), `task_id` (UUID FK to task), `title` (varchar), `completed` (boolean, default false), `position` (varchar(50)), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** indexes exist on `board.goal_id`, `column.board_id`, `task.column_id`, and `subtask.task_id`

#### Scenario: Migration converts integer positions to fractional index strings
- **WHEN** the migration runs on a database with existing boards
- **THEN** all existing column `position` values are converted from integers to fractional index strings that preserve the original ordering
- **AND** all existing task `position` values are converted from integers to fractional index strings that preserve the original ordering

## ADDED Requirements

### Requirement: Subtask Data Model
The system SHALL store subtasks as database records with the following fields: `id` (UUID primary key), `task_id` (FK to Task), `title` (string), `completed` (boolean, default false), `position` (varchar(50), fractional index string for ordering), `created_at`, and `updated_at`. Subtasks SHALL be returned ordered by `position` ascending (lexicographic sort) within their parent task. Subtasks are single-level only — no nested subtasks.

#### Scenario: Subtask created for a task
- **WHEN** a user creates a subtask with title "Research visa requirements" for a task
- **THEN** a Subtask record is created with `completed` set to false and a fractional index `position`

#### Scenario: Subtask ordering within task
- **WHEN** a task has 3 subtasks with fractional index positions
- **THEN** subtasks are returned in lexicographic position order

### Requirement: List Boards Endpoint
The system SHALL expose `GET /api/boards` as an authenticated endpoint that returns all boards belonging to the authenticated user. Each board in the response SHALL include summary data: `id`, `goal_id`, `title`, `goal_title`, `column_count`, `task_count`, `completed_task_count` (tasks in the last column by position), and `created_at`. Boards SHALL be ordered by `created_at` descending (newest first).

#### Scenario: User retrieves their boards
- **WHEN** an authenticated user with 3 boards sends `GET /api/boards`
- **THEN** the response contains 3 board summary objects ordered by creation date descending

#### Scenario: User with no boards gets empty list
- **WHEN** an authenticated user with no boards sends `GET /api/boards`
- **THEN** the response contains an empty array

#### Scenario: Board list includes progress data
- **WHEN** a board has 4 columns and 12 tasks total, with 3 tasks in the last column
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

### Requirement: Create Column Endpoint
The system SHALL expose `POST /api/boards/:id/columns` as an authenticated endpoint that creates a new column on the board. The request body SHALL include `title` and optionally `description`. The new column SHALL be assigned a fractional index position after the last existing column. The endpoint SHALL validate board ownership.

#### Scenario: Create column at end of board
- **WHEN** an authenticated user sends `POST /api/boards/:id/columns` with `{"title": "Review"}`
- **THEN** a new column is created with the given title, an empty description, and a position after all existing columns
- **AND** the response status is 201 with the created column data

#### Scenario: Create column on empty board
- **WHEN** a board has no columns and a user creates a column
- **THEN** the column is created with an initial fractional index position

### Requirement: Update Column Endpoint
The system SHALL expose `PATCH /api/columns/:id` as an authenticated endpoint that updates a column's title, description, and/or position. The endpoint SHALL validate ownership by tracing column → board → goal → user. When position is updated, only the target column's position field changes (no sibling renumbering).

#### Scenario: Rename column
- **WHEN** an authenticated user sends `PATCH /api/columns/:id` with `{"title": "In Review"}`
- **THEN** the column title is updated and the response contains the updated column

#### Scenario: Reorder column
- **WHEN** an authenticated user sends `PATCH /api/columns/:id` with `{"position": "a0V"}`
- **THEN** the column position is updated without modifying other columns' positions

#### Scenario: Update column on another user's board rejected
- **WHEN** user A sends `PATCH /api/columns/:id` for a column on user B's board
- **THEN** the response status is 404

### Requirement: Delete Column Endpoint
The system SHALL expose `DELETE /api/columns/:id` as an authenticated endpoint. When the column contains tasks, the request MUST include a `target_column_id` query parameter specifying another column on the same board to receive the tasks. Tasks SHALL be moved to the target column with new fractional index positions appended after the target column's existing tasks. When the column is empty, `target_column_id` is optional. The endpoint SHALL validate ownership and that both columns belong to the same board.

#### Scenario: Delete empty column
- **WHEN** an authenticated user sends `DELETE /api/columns/:id` for a column with no tasks
- **THEN** the column is deleted and the response status is 204

#### Scenario: Delete column with tasks, moving to target
- **WHEN** a column has 5 tasks and the user sends `DELETE /api/columns/:id?target_column_id=<other>`
- **THEN** all 5 tasks are moved to the target column with positions appended after existing tasks
- **AND** the original column is deleted

#### Scenario: Delete column with tasks without target rejected
- **WHEN** a column has tasks and the user sends `DELETE /api/columns/:id` without `target_column_id`
- **THEN** the response status is 400 with an error indicating a target column is required

#### Scenario: Target column on different board rejected
- **WHEN** the user sends `DELETE /api/columns/:id?target_column_id=<column-on-other-board>`
- **THEN** the response status is 400

#### Scenario: Delete last column rejected
- **WHEN** the board has only one column and the user attempts to delete it
- **THEN** the response status is 400 with an error indicating the last column cannot be deleted

### Requirement: Create Task Endpoint
The system SHALL expose `POST /api/columns/:id/tasks` as an authenticated endpoint that creates a new task in the specified column. The request body SHALL include `title` and optionally `description`, `due_date`, `priority`, and `estimated_minutes`. The new task SHALL be assigned a fractional index position after the last existing task in the column. The endpoint SHALL validate ownership by tracing column → board → goal → user.

#### Scenario: Create task in column
- **WHEN** an authenticated user sends `POST /api/columns/:id/tasks` with `{"title": "Research flights"}`
- **THEN** a new task is created with the given title, position after existing tasks, and the response status is 201

#### Scenario: Create task with metadata
- **WHEN** a user creates a task with `{"title": "Book hotel", "priority": "high", "due_date": "2026-03-15"}`
- **THEN** the task is created with the specified metadata fields populated

### Requirement: Update Task Endpoint
The system SHALL expose `PATCH /api/tasks/:id` as an authenticated endpoint that updates any combination of task fields: `title`, `description`, `due_date`, `priority`, `estimated_minutes`, `column_id` (to move between columns), and `position` (to reorder). The endpoint SHALL validate ownership by tracing task → column → board → goal → user. When `column_id` is changed, the task is moved to the new column. When both `column_id` and `position` are provided, the task moves to the new column at the specified position.

#### Scenario: Update task title
- **WHEN** an authenticated user sends `PATCH /api/tasks/:id` with `{"title": "Updated title"}`
- **THEN** the task title is updated

#### Scenario: Move task to another column
- **WHEN** a user sends `PATCH /api/tasks/:id` with `{"column_id": "<other-column-id>", "position": "a1V"}`
- **THEN** the task is moved to the target column at the specified position

#### Scenario: Reorder task within column
- **WHEN** a user sends `PATCH /api/tasks/:id` with `{"position": "a0V"}`
- **THEN** the task position is updated without modifying other tasks

#### Scenario: Update task on another user's board rejected
- **WHEN** user A sends `PATCH /api/tasks/:id` for a task on user B's board
- **THEN** the response status is 404

#### Scenario: Move task to column on different board rejected
- **WHEN** a user sends `PATCH /api/tasks/:id` with a `column_id` belonging to a different board
- **THEN** the response status is 400

### Requirement: Delete Task Endpoint
The system SHALL expose `DELETE /api/tasks/:id` as an authenticated endpoint that deletes a task and all its subtasks. The endpoint SHALL validate ownership by tracing task → column → board → goal → user.

#### Scenario: Delete task
- **WHEN** an authenticated user sends `DELETE /api/tasks/:id`
- **THEN** the task and all its subtasks are deleted and the response status is 204

#### Scenario: Delete task on another user's board rejected
- **WHEN** user A sends `DELETE /api/tasks/:id` for a task on user B's board
- **THEN** the response status is 404

### Requirement: Create Subtask Endpoint
The system SHALL expose `POST /api/tasks/:id/subtasks` as an authenticated endpoint that creates a new subtask for the specified task. The request body SHALL include `title`. The new subtask SHALL be assigned a fractional index position after the last existing subtask. The endpoint SHALL validate ownership by tracing task → column → board → goal → user.

#### Scenario: Create subtask
- **WHEN** an authenticated user sends `POST /api/tasks/:id/subtasks` with `{"title": "Check visa requirements"}`
- **THEN** a new subtask is created with `completed: false` and a position after existing subtasks
- **AND** the response status is 201

### Requirement: Update Subtask Endpoint
The system SHALL expose `PATCH /api/subtasks/:id` as an authenticated endpoint that updates a subtask's `title`, `completed`, and/or `position` fields. The endpoint SHALL validate ownership by tracing subtask → task → column → board → goal → user.

#### Scenario: Toggle subtask completed
- **WHEN** a user sends `PATCH /api/subtasks/:id` with `{"completed": true}`
- **THEN** the subtask `completed` field is set to true

#### Scenario: Rename subtask
- **WHEN** a user sends `PATCH /api/subtasks/:id` with `{"title": "Updated subtask title"}`
- **THEN** the subtask title is updated

### Requirement: Delete Subtask Endpoint
The system SHALL expose `DELETE /api/subtasks/:id` as an authenticated endpoint that deletes a subtask. The endpoint SHALL validate ownership by tracing subtask → task → column → board → goal → user.

#### Scenario: Delete subtask
- **WHEN** an authenticated user sends `DELETE /api/subtasks/:id`
- **THEN** the subtask is deleted and the response status is 204
