## ADDED Requirements

### Requirement: Board Generation SSE Endpoint
The system SHALL expose `POST /api/goals/{goal_id}/generate-board/stream` as an authenticated SSE endpoint that returns `Content-Type: text/event-stream`. The endpoint SHALL validate goal ownership and generation eligibility (same checks as the existing JSON endpoint). The endpoint SHALL pipe the internal `generate_board_stream()` async generator directly to the client as SSE events. Each event SHALL have a `event:` field (event type) and a `data:` field (JSON payload). The endpoint SHALL emit the following event types:
- `skeleton_ready` — contains `board_id` (string), `board_title` (string), and `tasks` (array of objects with `id`, `title`, `is_goal_node`)
- `task_enriched` — contains `task_id` (string), `title` (string), indicating enrichment is complete for this task
- `generation_complete` — contains `board_id` (string) and `failed_tasks` (array of task IDs that failed enrichment, may be empty)
- `generation_error` — contains `error` (string with a user-friendly error message)

The endpoint SHALL keep the connection open until `generation_complete` or `generation_error` is emitted, then close. The endpoint SHALL return 404 if the goal does not belong to the authenticated user. The endpoint SHALL return 409 if the goal already has a board or is not in `answered` status.

#### Scenario: Successful board generation stream
- **WHEN** an authenticated user sends POST to `/api/goals/{goal_id}/generate-board/stream` for a goal in `answered` status
- **THEN** the response has `Content-Type: text/event-stream`, emits `skeleton_ready` with the board title and task titles, then multiple `task_enriched` events (one per task), then `generation_complete` with the board ID

#### Scenario: Generation error streamed to client
- **WHEN** the skeleton generation fails after all retries
- **THEN** the endpoint emits a `generation_error` event with a user-friendly error message and closes the connection

#### Scenario: Unauthorized goal access
- **WHEN** a user sends a stream request for another user's goal
- **THEN** the endpoint returns 404 (not an SSE stream)

#### Scenario: Goal already has a board
- **WHEN** a user sends a stream request for a goal that already has a board
- **THEN** the endpoint returns 409 with an error message

### Requirement: Full-Screen Generation Progress View
The system SHALL display a full-screen progress view on the goal creation page when the user clicks "Generate Board". The progress view SHALL replace the goal summary content in-place as a new step (`generating`) in the existing multi-step wizard. The view SHALL be vertically centered and occupy the full viewport height. The view SHALL display three elements: (1) a header area showing the board title once available, (2) a phase text indicator showing the current generation phase, and (3) a stack list of tasks.

#### Scenario: Transition from summary to progress view
- **WHEN** the user clicks "Generate Board" on the goal summary
- **THEN** the goal summary is replaced by the full-screen generation progress view

#### Scenario: Board title displayed after skeleton arrives
- **WHEN** the `skeleton_ready` SSE event is received with `board_title: "Relocation to Lisbon"`
- **THEN** the header area displays "Relocation to Lisbon"

#### Scenario: Progress view occupies full viewport
- **WHEN** the generation progress view is active
- **THEN** the view is centered vertically and fills the full viewport height

### Requirement: Generation Phase Text Indicator
The system SHALL display a phase text indicator that reflects the current stage of board generation. The phase text SHALL update through the following stages:
- Initial (before any SSE events): "Creating board structure..."
- After `skeleton_ready`: "Adding details (0/N)..." where N is the total task count from the skeleton
- After each `task_enriched`: "Adding details (X/N)..." where X increments
- After `generation_complete`: "Board ready!"
- After `generation_error`: "Generation failed"

The counter SHALL update in real-time as `task_enriched` events arrive.

#### Scenario: Phase shows skeleton creation
- **WHEN** the user clicks "Generate Board" and the SSE connection is established
- **THEN** the phase text reads "Creating board structure..."

#### Scenario: Phase shows enrichment progress
- **WHEN** `skeleton_ready` has arrived with 15 tasks and 5 `task_enriched` events have been received
- **THEN** the phase text reads "Adding details (5/15)..."

#### Scenario: Phase shows completion
- **WHEN** the `generation_complete` event is received
- **THEN** the phase text reads "Board ready!"

#### Scenario: Phase shows error
- **WHEN** a `generation_error` event is received
- **THEN** the phase text reads "Generation failed"

### Requirement: Task Stack List
The system SHALL display generated tasks as a reverse-chronological stack list where the most recently revealed task appears at the top. The stack list SHALL be limited to displaying 5-6 visible items. Tasks beyond the visible limit SHALL be hidden. The bottom of the visible list SHALL have a gradient fade from opaque to transparent, creating a visual sense of depth and continuation. Each task item SHALL display the task title and a status indicator distinguishing between skeleton-only (title received but not yet enriched) and enriched (enrichment complete) states.

#### Scenario: Skeleton tasks appear in stack
- **WHEN** the `skeleton_ready` event arrives with 15 tasks
- **THEN** all 15 task titles are added to the stack, with the last task in the list appearing at the top and only the top 5-6 visible. A gradient fade is visible at the bottom of the list.

#### Scenario: New task appears at top of stack
- **WHEN** a task is added to the stack (during skeleton reveal)
- **THEN** the task appears at the top of the list, pushing older tasks down

#### Scenario: Task enrichment updates status indicator
- **WHEN** a `task_enriched` event arrives for a task already in the stack
- **THEN** that task's status indicator changes from skeleton-only to enriched (e.g., a subtle checkmark or filled dot appears)

#### Scenario: Gradient fade at bottom of stack
- **WHEN** there are more than 6 tasks in the stack
- **THEN** the bottom of the visible list area fades to transparent via a CSS gradient overlay, hiding overflow tasks beneath

#### Scenario: Stack with fewer than 6 tasks
- **WHEN** the skeleton produces only 5 tasks
- **THEN** all 5 tasks are visible and no gradient fade is shown (or a minimal fade is shown at the bottom)

### Requirement: Skeleton Task Staggered Reveal Animation
The system SHALL reveal skeleton tasks with a staggered animation rather than showing all tasks instantly. When the `skeleton_ready` event arrives with N tasks, each task SHALL appear with a short delay between them (50-100ms apart), creating a cascading "building" effect. The animation SHALL complete within 2 seconds regardless of the number of tasks (delay adjusted proportionally).

#### Scenario: 15 tasks revealed with stagger
- **WHEN** `skeleton_ready` arrives with 15 tasks
- **THEN** tasks appear one by one from bottom to top of the stack with ~100ms between each, completing within ~1.5 seconds

#### Scenario: 5 tasks revealed with stagger
- **WHEN** `skeleton_ready` arrives with 5 tasks
- **THEN** tasks appear one by one with delays, completing quickly

### Requirement: Auto-Navigation on Generation Complete
The system SHALL automatically navigate to the generated board's page (`/boards/{boardId}`) after generation completes. A brief delay of approximately 1.5 seconds SHALL elapse between the `generation_complete` event and navigation, allowing the user to see the "Board ready!" state. If the user is no longer on the generation page when the timer fires (e.g., they navigated away), the navigation SHALL NOT occur.

#### Scenario: Auto-navigate after successful generation
- **WHEN** the `generation_complete` event is received with `board_id: "abc123"`
- **THEN** after approximately 1.5 seconds, the browser navigates to `/boards/abc123`

#### Scenario: User navigated away before timer
- **WHEN** the `generation_complete` event fires but the user has already navigated to a different page
- **THEN** the auto-navigation does not occur

### Requirement: Generation Error Recovery
The system SHALL handle generation errors and SSE connection failures gracefully. When a `generation_error` event is received or the SSE connection drops unexpectedly, the progress view SHALL display an error message and a "Try Again" button. Clicking "Try Again" SHALL reset the progress view and re-initiate the SSE connection to restart generation. If the connection drops after `skeleton_ready` but before `generation_complete`, the error message SHALL include a note that the board may have been partially created, with a link to check the boards list.

#### Scenario: Generation error with retry
- **WHEN** a `generation_error` event is received with `error: "AI generation failed"`
- **THEN** the phase text shows "Generation failed", an error message is displayed, and a "Try Again" button is available

#### Scenario: Connection drops mid-generation
- **WHEN** the SSE connection drops after `skeleton_ready` but before `generation_complete`
- **THEN** an error message is displayed: "Connection lost. Your board may have been partially created." with a "Try Again" button and a "Check your boards" link

#### Scenario: Retry restarts generation
- **WHEN** the user clicks "Try Again" after an error (and no board was created)
- **THEN** the progress view resets and a new SSE connection is established

### Requirement: SSE Client Hook
The system SHALL provide a React hook `useBoardGenerationStream` that manages the SSE connection lifecycle for board generation. The hook SHALL accept a `goalId` parameter and return the current generation state including: `phase` (string: "connecting" | "skeleton" | "enriching" | "complete" | "error"), `boardTitle` (string | null), `tasks` (array of task objects with id, title, and isEnriched boolean), `enrichedCount` (number), `totalCount` (number), `boardId` (string | null), `error` (string | null), and a `start()` function to initiate the connection. The hook SHALL handle connection cleanup on component unmount. The hook SHALL use a fetch-based SSE approach (not native `EventSource`) to support POST method and Authorization headers.

#### Scenario: Hook starts SSE connection
- **WHEN** `start()` is called on the hook
- **THEN** a POST fetch request with `Accept: text/event-stream` is made to `/api/goals/{goalId}/generate-board/stream` with the auth token

#### Scenario: Hook processes skeleton event
- **WHEN** a `skeleton_ready` event is received
- **THEN** the hook updates `phase` to "enriching", sets `boardTitle`, populates `tasks` with skeleton data, and sets `totalCount`

#### Scenario: Hook processes enrichment event
- **WHEN** a `task_enriched` event is received
- **THEN** the hook marks the corresponding task as enriched and increments `enrichedCount`

#### Scenario: Hook cleans up on unmount
- **WHEN** the component using the hook unmounts
- **THEN** the SSE connection is aborted via `AbortController`
