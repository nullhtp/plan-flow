# board-management Specification

## Purpose
TBD - created by archiving change add-board-generation. Update Purpose after archive.
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

### Requirement: Column Data Model
The system SHALL store columns as database records with the following fields: `id` (UUID primary key), `board_id` (FK to Board), `title` (string), `description` (string), `position` (integer for ordering), `created_at`, and `updated_at`. Columns SHALL be returned ordered by `position` ascending.

#### Scenario: Columns created with AI-assigned positions
- **WHEN** a board is generated with 5 columns
- **THEN** each column record has a unique `position` value (0-4) and columns are retrievable in position order

#### Scenario: Column belongs to a board
- **WHEN** a column is created
- **THEN** it MUST reference a valid board via `board_id`

### Requirement: Task Data Model
The system SHALL store tasks as database records with the following fields: `id` (UUID primary key), `column_id` (FK to Column), `title` (string), `description` (string), `position` (integer for ordering), `due_date` (date, nullable), `priority` (string enum: "low"/"medium"/"high", nullable), `estimated_minutes` (integer, nullable), `created_at`, and `updated_at`. Tasks SHALL be returned ordered by `position` ascending within their column. The progressive metadata fields (`due_date`, `priority`, `estimated_minutes`) SHALL be nullable — the AI populates them per-task only when relevant to the goal type and specific task.

#### Scenario: Task created with full progressive metadata
- **WHEN** the AI generates a "Book flight to Lisbon" task for a relocation goal
- **THEN** the task record MAY include `due_date`, `priority: "high"`, and `estimated_minutes: 30`

#### Scenario: Task created without progressive metadata
- **WHEN** the AI generates a "Brainstorm potential neighborhoods" task
- **THEN** the task record MAY have `due_date`, `priority`, and `estimated_minutes` all set to null

#### Scenario: Tasks ordered within column
- **WHEN** a column contains 4 tasks with positions 0, 1, 2, 3
- **THEN** tasks are returned in position order (0 first, 3 last)

### Requirement: Board Persistence Service
The system SHALL implement a board persistence service that takes AI-generated board output and creates Board, Column, and Task records in a single database transaction. If any part of the persistence fails, the entire transaction SHALL be rolled back. The service SHALL be located in `app/domains/boards/service.py`.

#### Scenario: Successful board persistence
- **WHEN** the AI generates a board with 4 columns and 20 tasks
- **THEN** 1 Board record, 4 Column records, and 20 Task records are created in a single transaction

#### Scenario: Persistence rollback on failure
- **WHEN** a database error occurs while creating the 15th task
- **THEN** no Board, Column, or Task records are persisted (full rollback)

### Requirement: Generate Board Endpoint
The system SHALL expose `POST /api/goals/:id/generate-board` as an authenticated endpoint. The endpoint SHALL validate that the goal exists, belongs to the authenticated user, is in `answered` status, and does not already have a board. It SHALL then trigger the AI board generation pipeline, persist the result, transition the goal status to `active`, and return the full board with nested columns and tasks. The response SHALL use HTTP 201 on success.

#### Scenario: Successful board generation
- **WHEN** an authenticated user sends `POST /api/goals/:id/generate-board` for their goal in `answered` status
- **THEN** the response status is 201 and the body contains the board with `id`, `title`, `goal_id`, and nested `columns` (each with `id`, `title`, `description`, `position`, and nested `tasks`)

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

### Requirement: Get Board Endpoint
The system SHALL expose `GET /api/boards/:id` as an authenticated endpoint that returns the board with its nested columns and tasks. Each column SHALL include its tasks ordered by position. Columns SHALL be ordered by position. Users SHALL only be able to retrieve boards for their own goals.

#### Scenario: Retrieve board with nested data
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a board belonging to their goal
- **THEN** the response includes the board fields, an array of columns (each with title, description, position), and each column includes an array of tasks (each with title, description, position, and progressive metadata)

#### Scenario: Retrieve another user's board
- **WHEN** user A requests `GET /api/boards/:id` for a board belonging to user B's goal
- **THEN** the response status is 404

#### Scenario: Board not found
- **WHEN** a user requests `GET /api/boards/:id` with a non-existent board ID
- **THEN** the response status is 404

### Requirement: Board Alembic Migration
The system SHALL include an Alembic migration that creates the `board`, `column`, and `task` tables with all required columns, foreign keys, indexes, and constraints. The migration SHALL add an index on `board.goal_id`, `column.board_id`, and `task.column_id`.

#### Scenario: Migration creates board tables
- **WHEN** `alembic upgrade head` is run
- **THEN** the `board` table exists with columns: `id` (UUID PK), `goal_id` (UUID FK to goal, unique), `title` (varchar), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** the `column` table exists with columns: `id` (UUID PK), `board_id` (UUID FK to board), `title` (varchar), `description` (text), `position` (integer), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** the `task` table exists with columns: `id` (UUID PK), `column_id` (UUID FK to column), `title` (varchar), `description` (text), `position` (integer), `due_date` (date, nullable), `priority` (varchar, nullable), `estimated_minutes` (integer, nullable), `created_at` (timestamptz), `updated_at` (timestamptz)
- **AND** indexes exist on `board.goal_id`, `column.board_id`, and `task.column_id`

