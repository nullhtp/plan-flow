## ADDED Requirements

### Requirement: Sub-Board Generation SSE Endpoint
The system SHALL expose `POST /api/tasks/{task_id}/generate-sub-board/stream` as an authenticated SSE endpoint that returns `Content-Type: text/event-stream`. The endpoint SHALL validate task ownership, nesting depth (reject sub-boards of sub-boards), and that no sub-board already exists for the task. The endpoint SHALL accept the same request body as the existing JSON endpoint (`SubBoardGenerateRequest` with answers array). The endpoint SHALL resolve goal context, delete existing subtasks, auto-start the parent task, then pipe the internal `generate_sub_board_stream()` async generator through a persistence layer and forward SSE events to the client. Each event SHALL have an `event:` field (event type) and a `data:` field (JSON payload). The endpoint SHALL emit the same event types as the main board generation SSE endpoint:
- `skeleton_ready` -- contains `board_id` (string), `board_title` (string), and `tasks` (array of objects with `id`, `title`, `is_goal_node`)
- `task_enriched` -- contains `task_id` (string), `title` (string)
- `generation_complete` -- contains `board_id` (string) and `failed_tasks` (array of task IDs that failed enrichment, may be empty)
- `generation_error` -- contains `error` (string with a user-friendly error message)

The endpoint SHALL keep the connection open until `generation_complete` or `generation_error` is emitted, then close. The endpoint SHALL return 404 if the task does not belong to the authenticated user. The endpoint SHALL return 409 if the task already has a sub-board. The endpoint SHALL return 422 if the task belongs to a sub-board (nesting depth exceeded).

#### Scenario: Successful sub-board generation stream
- **WHEN** an authenticated user sends POST to `/api/tasks/{task_id}/generate-sub-board/stream` with valid answers for a task on a root board
- **THEN** the response has `Content-Type: text/event-stream`, emits `skeleton_ready` with the sub-board title and task titles, then multiple `task_enriched` events, then `generation_complete` with the sub-board ID

#### Scenario: Generation error streamed to client
- **WHEN** the skeleton generation fails after all retries
- **THEN** the endpoint emits a `generation_error` event with a user-friendly error message and closes the connection

#### Scenario: Task already has a sub-board
- **WHEN** a user sends a stream request for a task that already has a sub-board
- **THEN** the endpoint returns 409 with an error message (not an SSE stream)

#### Scenario: Task on a sub-board (nesting depth exceeded)
- **WHEN** a user sends a stream request for a task that belongs to a sub-board
- **THEN** the endpoint returns 422 with an error message about nesting depth

#### Scenario: Unauthorized task access
- **WHEN** a user sends a stream request for another user's task
- **THEN** the endpoint returns 404 (not an SSE stream)

### Requirement: Generalized Generation Progress Component
The system SHALL provide a generalized `BoardGenerationProgress` component and `useBoardGenerationStream` hook that can be used for both main board generation and sub-board generation. The hook SHALL accept a configurable SSE URL parameter instead of being hardcoded to the goal-based endpoint. The component SHALL accept an optional `onComplete(boardId: string)` callback for custom navigation behavior upon generation completion. Both the main board generation page and the sub-board expansion page SHALL use the same component and hook, ensuring identical visual treatment (progress bar, task stack, phase text, staggered animation, error handling).

#### Scenario: Hook used for main board generation
- **WHEN** the main board generation page initializes the hook
- **THEN** the hook connects to `/api/goals/{goalId}/generate-board/stream` and processes SSE events identically to the current behavior

#### Scenario: Hook used for sub-board generation
- **WHEN** the sub-board expansion page initializes the hook
- **THEN** the hook connects to `/api/tasks/{taskId}/generate-sub-board/stream` and processes SSE events identically to main board generation (same event types, same state transitions)

#### Scenario: Identical visual treatment for both flows
- **WHEN** either flow is in the `enriching` phase with 5 of 10 tasks enriched
- **THEN** both display the same progress bar at 50%, the same task stack with staggered animation, and the same phase text "5 / 10 tasks enriched"
