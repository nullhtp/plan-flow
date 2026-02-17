## ADDED Requirements

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

## MODIFIED Requirements

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
