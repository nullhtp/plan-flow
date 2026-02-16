## MODIFIED Requirements

### Requirement: Generate Board Endpoint
The system SHALL expose `POST /api/goals/:id/generate-board` as an authenticated SSE (Server-Sent Events) streaming endpoint. The endpoint SHALL return `Content-Type: text/event-stream`. The endpoint SHALL validate that the goal exists, belongs to the authenticated user, is in `answered` status, and does not already have a board. It SHALL then trigger the two-step AI board generation pipeline (skeleton + parallel enrichment), streaming progress events to the client as generation proceeds. The endpoint SHALL emit the following SSE events: (1) `skeleton_ready` — emitted after the skeleton is generated and Board/Task records are persisted, containing the board structure with task IDs, titles, dependency edges, and goal node flag; (2) `task_enriched` — emitted once per task as each parallel enrichment completes and the task record is updated, containing the task's description, metadata, and subtasks; (3) `generation_complete` — emitted after all enrichment completes, containing the board ID and a list of any failed task IDs; (4) `generation_error` — emitted if an unrecoverable error occurs (e.g., skeleton generation fails after all retries), containing an error message. The goal status SHALL transition to `generating` before generation starts, and to `active` after `generation_complete` is emitted. If generation fails entirely, the goal status SHALL revert to `answered`.

#### Scenario: Successful streaming board generation
- **WHEN** an authenticated user sends `POST /api/goals/:id/generate-board` for their goal in `answered` status
- **THEN** the response `Content-Type` is `text/event-stream`
- **AND** the first event is `skeleton_ready` with board structure (task IDs, titles, edges)
- **AND** subsequent events are `task_enriched` (one per task, in completion order)
- **AND** the final event is `generation_complete` with the board ID

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
