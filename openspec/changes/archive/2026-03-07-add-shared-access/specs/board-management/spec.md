## ADDED Requirements

### Requirement: Board Share Data Model
The system SHALL store board share links as records in a `board_share` table with the following fields: `id` (UUID primary key), `board_id` (FK to Board, unique — one share link per board), `token` (varchar(64), unique, URL-safe random string), `created_by` (FK to User — the board owner who created the link), `created_at` (timestamptz). The `board_id` MUST reference a root board (one with `goal_id` set). A unique constraint on `board_id` SHALL ensure only one active share link exists per board. The token SHALL be generated using `secrets.token_urlsafe(32)`. When the board is deleted, the share record SHALL be cascade-deleted.

#### Scenario: Share link created for a board
- **WHEN** the owner creates a share link for their board
- **THEN** a BoardShare record is created with a unique 43-character URL-safe token and `created_by` set to the owner's user ID

#### Scenario: Only one share link per board
- **WHEN** a share link already exists for a board and the owner creates a new one
- **THEN** the existing share record's token is regenerated (old link invalidated)

#### Scenario: Share link cascade-deleted with board
- **WHEN** a board with an active share link is deleted
- **THEN** the BoardShare record is also deleted

#### Scenario: Share link only for root boards
- **WHEN** an attempt is made to create a share link for a sub-board
- **THEN** the system SHALL reject with a validation error indicating only root boards can be shared

### Requirement: Board Member Data Model
The system SHALL store board collaborators as records in a `board_member` table with the following fields: `id` (UUID primary key), `board_id` (FK to Board), `user_id` (FK to User), `role` (varchar, default "collaborator"), `joined_at` (timestamptz). A unique constraint on `(board_id, user_id)` SHALL prevent duplicate memberships. The `board_id` MUST reference a root board. When the board is deleted, all member records SHALL be cascade-deleted. The board owner SHALL NOT be stored as a member — ownership is determined via the goal's `user_id`.

#### Scenario: Member added via share link redemption
- **WHEN** an authenticated user redeems a valid share token
- **THEN** a BoardMember record is created with `role` set to "collaborator" and `joined_at` set to the current time

#### Scenario: Duplicate membership prevented
- **WHEN** a user who is already a member attempts to redeem the same share token again
- **THEN** the system SHALL return success without creating a duplicate record (idempotent)

#### Scenario: Owner cannot become a member of own board
- **WHEN** the board owner redeems the share token for their own board
- **THEN** the system SHALL return success without creating a member record (owner already has full access)

#### Scenario: Members cascade-deleted with board
- **WHEN** a board with 3 collaborators is deleted
- **THEN** all 3 BoardMember records are also deleted

### Requirement: Share Link Management Endpoints
The system SHALL expose endpoints for managing board share links, restricted to the board owner:

- `POST /api/boards/:id/share` — Create or regenerate a share link for the board. Returns the share token and a shareable URL. If a link already exists, the token is regenerated (old link invalidated). Restricted to root boards.
- `GET /api/boards/:id/share` — Get the current share link for the board. Returns 404 if no link exists.
- `DELETE /api/boards/:id/share` — Delete the share link, preventing new users from joining. Existing members retain access until individually revoked.

All endpoints SHALL validate that the board exists and the authenticated user is the board owner (not just a collaborator).

#### Scenario: Owner creates share link
- **WHEN** the board owner sends `POST /api/boards/:id/share` for a board without an existing link
- **THEN** a new share link is created and the response contains `{ token, url }` with status 201

#### Scenario: Owner regenerates share link
- **WHEN** the board owner sends `POST /api/boards/:id/share` for a board with an existing link
- **THEN** the token is regenerated and the response contains the new `{ token, url }` with status 200

#### Scenario: Owner retrieves share link
- **WHEN** the board owner sends `GET /api/boards/:id/share`
- **THEN** the response contains the current `{ token, url, created_at }`

#### Scenario: No share link exists
- **WHEN** the board owner sends `GET /api/boards/:id/share` for a board without a share link
- **THEN** the response status is 404

#### Scenario: Owner deletes share link
- **WHEN** the board owner sends `DELETE /api/boards/:id/share`
- **THEN** the share link is deleted (status 204) and the token can no longer be used to join

#### Scenario: Collaborator cannot manage share link
- **WHEN** a collaborator sends `POST /api/boards/:id/share`
- **THEN** the response status is 403

#### Scenario: Non-member cannot manage share link
- **WHEN** a user with no access to the board sends `POST /api/boards/:id/share`
- **THEN** the response status is 404

### Requirement: Join Board via Share Token Endpoint
The system SHALL expose `POST /api/boards/join` as an authenticated endpoint that accepts `{ token: string }` in the request body. The endpoint SHALL validate the token, resolve the associated board, and add the authenticated user as a collaborator. If the user is already a member or the owner, the endpoint SHALL return success idempotently. The response SHALL include the board ID and title so the frontend can navigate to the board.

#### Scenario: User joins board via valid token
- **WHEN** an authenticated user sends `POST /api/boards/join` with a valid share token
- **THEN** a BoardMember record is created and the response contains `{ board_id, board_title, role: "collaborator" }` with status 200

#### Scenario: Invalid token rejected
- **WHEN** a user sends `POST /api/boards/join` with an invalid or expired token
- **THEN** the response status is 404 with an error indicating the share link is invalid

#### Scenario: Owner redeems own token
- **WHEN** the board owner sends `POST /api/boards/join` with their board's share token
- **THEN** the response contains `{ board_id, board_title, role: "owner" }` with status 200 (no member record created)

#### Scenario: Already-member redeems token again
- **WHEN** a collaborator sends `POST /api/boards/join` with the same token again
- **THEN** the response contains `{ board_id, board_title, role: "collaborator" }` with status 200 (idempotent)

#### Scenario: Unauthenticated user rejected
- **WHEN** an unauthenticated user sends `POST /api/boards/join`
- **THEN** the response status is 401

### Requirement: Board Member Management Endpoints
The system SHALL expose endpoints for managing board members, restricted to the board owner:

- `GET /api/boards/:id/members` — List all members of the board. Returns member records with user details (id, email, joined_at, role). The owner is included in the response with `role: "owner"` but is not stored as a BoardMember.
- `DELETE /api/boards/:id/members/:user_id` — Remove a collaborator from the board. The owner cannot be removed. The removed user immediately loses access.

#### Scenario: Owner lists board members
- **WHEN** the board owner sends `GET /api/boards/:id/members` for a board with 2 collaborators
- **THEN** the response contains 3 entries: the owner (role "owner") and 2 collaborators (role "collaborator")

#### Scenario: Owner revokes a collaborator
- **WHEN** the board owner sends `DELETE /api/boards/:id/members/:user_id` for a collaborator
- **THEN** the BoardMember record is deleted (status 204) and the user can no longer access the board

#### Scenario: Owner cannot remove themselves
- **WHEN** the board owner sends `DELETE /api/boards/:id/members/:user_id` with their own user ID
- **THEN** the response status is 400 with an error indicating the owner cannot be removed

#### Scenario: Collaborator cannot manage members
- **WHEN** a collaborator sends `DELETE /api/boards/:id/members/:user_id`
- **THEN** the response status is 403

#### Scenario: Removing non-existent member
- **WHEN** the board owner sends `DELETE /api/boards/:id/members/:user_id` for a user who is not a member
- **THEN** the response status is 404

### Requirement: Shared Access Alembic Migration
The system SHALL include an Alembic migration that creates the `board_share` and `board_member` tables. The `board_share` table SHALL have columns: `id` (UUID PK), `board_id` (UUID FK to board, unique), `token` (varchar(64), unique), `created_by` (UUID FK to user), `created_at` (timestamptz). The `board_member` table SHALL have columns: `id` (UUID PK), `board_id` (UUID FK to board), `user_id` (UUID FK to user), `role` (varchar, default "collaborator"), `joined_at` (timestamptz). A unique constraint SHALL exist on `(board_id, user_id)` in `board_member`. Both tables SHALL have ON DELETE CASCADE for the `board_id` foreign key. Indexes SHALL exist on `board_share.token`, `board_member.board_id`, and `board_member.user_id`.

#### Scenario: Migration creates shared access tables
- **WHEN** `alembic upgrade head` is run
- **THEN** the `board_share` table exists with all specified columns, foreign keys, and a unique index on `token`
- **AND** the `board_member` table exists with all specified columns, foreign keys, a unique constraint on `(board_id, user_id)`, and indexes on `board_id` and `user_id`

### Requirement: Shared Board in Board List
The system SHALL support listing shared boards via `GET /api/boards?shared=true`. When `shared=true`, the endpoint returns boards where the authenticated user is a collaborator (has a BoardMember record). Each board in the response SHALL include a `role` field: "owner" for owned boards (default list) and "collaborator" for shared boards. The default `GET /api/boards` (without `shared=true`) continues to return only owned boards but now includes `role: "owner"` in each entry.

#### Scenario: User retrieves shared boards
- **WHEN** an authenticated user who is a collaborator on 2 boards sends `GET /api/boards?shared=true`
- **THEN** the response contains 2 board summary objects, each with `role: "collaborator"`

#### Scenario: User with no shared boards
- **WHEN** an authenticated user who is not a collaborator on any board sends `GET /api/boards?shared=true`
- **THEN** the response contains an empty array

#### Scenario: Owned boards include role field
- **WHEN** an authenticated user sends `GET /api/boards` (without shared param)
- **THEN** each board summary includes `role: "owner"`

## MODIFIED Requirements

### Requirement: Board Persistence Service
The system SHALL implement board persistence as a set of focused service modules split by entity. **Board operations** (`app/domains/boards/board_service.py`): board CRUD, board listing with summary data, board response building, and share link/member management. **Task operations** (`app/domains/boards/task_service.py`): task CRUD, status transition validation, dependency query helpers, and board generation orchestration (consuming AI stream, persisting skeleton, running enrichment, managing goal state transitions via `goals/service.py`). **Subtask operations** (`app/domains/boards/subtask_service.py`): subtask CRUD with fractional index positioning. Fractional indexing utilities SHALL be extracted to `app/domains/boards/position_utils.py`. Ownership validation SHALL be extracted to `app/domains/boards/ownership.py` and shared across boards and AI domains. Access validation SHALL check both ownership (via goal.user_id) and membership (via board_member table) — the owner has full access while collaborators can perform all operations except board deletion and share/member management. All services SHALL use repository classes for database access instead of direct SQLAlchemy session calls. **Phase 1 (Skeleton persistence):** After the AI generates the board skeleton, the task service SHALL create Board and Task records (with titles but empty descriptions) and TaskDependency records in a single database transaction. The service SHALL validate that the dependency graph forms a valid DAG (no cycles) before persisting. The service SHALL return a mapping of AI task IDs to database UUIDs. **Phase 2 (Enrichment persistence):** As each task enrichment completes, the task service SHALL update the corresponding Task record with the description and progressive metadata, and create Subtask records for the generated subtasks, each in its own transaction.

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

#### Scenario: Collaborator can edit tasks on shared board
- **WHEN** a collaborator creates or updates a task on a board they were invited to
- **THEN** the operation succeeds with the same behavior as the owner

#### Scenario: Collaborator cannot delete the board
- **WHEN** a collaborator attempts to delete a board they were invited to
- **THEN** the system SHALL reject with 403 Forbidden

### Requirement: Get Board Endpoint
The system SHALL expose `GET /api/boards/:id` as an authenticated endpoint that returns the board with its nested tasks, subtasks, and dependency edges. Each task SHALL include its subtasks ordered by position, a list of `dependency_ids` (tasks it depends on), and a list of `dependent_ids` (tasks that depend on it). A computed `is_locked` boolean SHALL indicate whether all dependencies have status `done`. Each task SHALL include a `sub_board_id` field (nullable string) — set to the ID of the task's sub-board if one exists, null otherwise. Each task SHALL include `sub_board_progress` (nullable object with `task_count` and `completed_task_count`) when a sub-board exists. The board response SHALL include `parent_task_id` (nullable string) and `parent_board` (nullable object with `id` and `title`) for breadcrumb navigation. The board response SHALL include a `role` field indicating the authenticated user's relationship to the board: "owner" if they own the goal, "collaborator" if they are a board member. Users SHALL be able to retrieve boards they own (via goal) OR boards where they are a collaborator (via board_member). For sub-boards, access is inherited from the root board.

#### Scenario: Retrieve board with nested data and dependencies
- **WHEN** an authenticated user requests `GET /api/boards/:id` for a board they have access to
- **THEN** the response includes the board fields, an array of tasks (each with title, description, status, `is_goal_node`, progressive metadata, nested subtasks, `dependency_ids`, `dependent_ids`, `is_locked`, `sub_board_id`, `sub_board_progress`), an `edges` array of `{source, target}` pairs, and a `role` field

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

#### Scenario: Collaborator retrieves shared board
- **WHEN** a collaborator requests `GET /api/boards/:id` for a board they are a member of
- **THEN** the response includes all board data with `role: "collaborator"`

#### Scenario: Non-member retrieves board
- **WHEN** a user with no access requests `GET /api/boards/:id`
- **THEN** the response status is 404

#### Scenario: Board not found
- **WHEN** a user requests `GET /api/boards/:id` with a non-existent board ID
- **THEN** the response status is 404

### Requirement: List Boards Endpoint
The system SHALL expose `GET /api/boards` as an authenticated endpoint that returns all root-level boards belonging to the authenticated user. Only boards with `parent_task_id IS NULL` SHALL be returned (sub-boards are excluded). Each board in the response SHALL include summary data: `id`, `goal_id`, `title`, `goal_title`, `task_count`, `completed_task_count` (tasks with status `done`), `created_at`, and `role` ("owner" or "collaborator"). Boards SHALL be ordered by `created_at` descending (newest first). When the query parameter `shared=true` is passed, the endpoint SHALL return boards where the user is a collaborator instead of owned boards.

#### Scenario: User retrieves their boards
- **WHEN** an authenticated user with 3 root boards and 2 sub-boards sends `GET /api/boards`
- **THEN** the response contains 3 board summary objects ordered by creation date descending (sub-boards excluded), each with `role: "owner"`

#### Scenario: User with no boards gets empty list
- **WHEN** an authenticated user with no boards sends `GET /api/boards`
- **THEN** the response contains an empty array

#### Scenario: Board list includes progress data
- **WHEN** a board has 12 tasks total, with 3 tasks having status `done`
- **THEN** the board summary shows `task_count: 12` and `completed_task_count: 3`

#### Scenario: Unauthenticated request rejected
- **WHEN** an unauthenticated user sends `GET /api/boards`
- **THEN** the response status is 401

#### Scenario: User retrieves shared boards
- **WHEN** a user who is a collaborator on 2 boards sends `GET /api/boards?shared=true`
- **THEN** the response contains 2 board summary objects, each with `role: "collaborator"`
