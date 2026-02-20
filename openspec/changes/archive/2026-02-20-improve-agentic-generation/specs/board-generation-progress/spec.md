## MODIFIED Requirements

### Requirement: Board Generation SSE Endpoint
The system SHALL expose `POST /api/goals/{goal_id}/generate-board/stream` as an authenticated SSE endpoint that returns `Content-Type: text/event-stream`. The endpoint SHALL validate goal ownership and generation eligibility (same checks as the existing JSON endpoint). The endpoint SHALL pipe the internal `generate_board_stream()` async generator directly to the client as SSE events. Each event SHALL have a `event:` field (event type) and a `data:` field (JSON payload). The endpoint SHALL emit the following event types:
- `research_started` — contains `query_count` (integer — number of search queries being executed)
- `research_progress` — contains `query` (string — the search query being executed), `results_count` (integer — number of results found for this query), and `queries_completed` (integer — total queries completed so far)
- `research_complete` — contains `total_results` (integer — total unique results gathered), `total_queries` (integer — queries executed), and `urls_fetched` (integer — number of full-page extractions performed)
- `skeleton_ready` — contains `board_id` (string), `board_title` (string), and `tasks` (array of objects with `id`, `title`, `is_goal_node`)
- `task_enriched` — contains `task_id` (string), `title` (string), indicating enrichment is complete for this task
- `generation_complete` — contains `board_id` (string) and `failed_tasks` (array of task IDs that failed enrichment, may be empty)
- `generation_error` — contains `error` (string with a user-friendly error message)

When Tavily is not configured, the research events (`research_started`, `research_progress`, `research_complete`) SHALL NOT be emitted and generation proceeds directly to skeleton generation. The endpoint SHALL keep the connection open until `generation_complete` or `generation_error` is emitted, then close. The endpoint SHALL return 404 if the goal does not belong to the authenticated user. The endpoint SHALL return 409 if the goal already has a board or is not in `answered` status.

#### Scenario: Successful board generation stream with research
- **WHEN** an authenticated user sends POST to `/api/goals/{goal_id}/generate-board/stream` for a goal in `answered` status and Tavily is configured
- **THEN** the response has `Content-Type: text/event-stream`, emits `research_started`, one or more `research_progress` events, `research_complete`, `skeleton_ready` with the board title and task titles, then multiple `task_enriched` events (one per task), then `generation_complete` with the board ID

#### Scenario: Successful board generation stream without research
- **WHEN** an authenticated user sends POST to `/api/goals/{goal_id}/generate-board/stream` for a goal in `answered` status and Tavily is NOT configured
- **THEN** the response emits `skeleton_ready`, then `task_enriched` events, then `generation_complete` (no research events)

#### Scenario: Generation error streamed to client
- **WHEN** the skeleton generation fails after all retries
- **THEN** the endpoint emits a `generation_error` event with a user-friendly error message and closes the connection

#### Scenario: Unauthorized goal access
- **WHEN** a user sends a stream request for another user's goal
- **THEN** the endpoint returns 404 (not an SSE stream)

#### Scenario: Goal already has a board
- **WHEN** a user sends a stream request for a goal that already has a board
- **THEN** the endpoint returns 409 with an error message

### Requirement: Generation Phase Text Indicator
The system SHALL display a phase text indicator that reflects the current stage of board generation. The phase text SHALL update through the following stages:
- Initial (before any SSE events): "Analyzing your goal..."
- After `research_started`: "Researching (0/N)..." where N is the query count from the event
- After each `research_progress`: "Researching (X/N)..." where X is `queries_completed` from the event, with the current query text displayed as a subtitle (e.g., "Searching: apartment rental prices Lisbon 2026")
- After `research_complete`: "Creating board structure..."
- After `skeleton_ready`: "Adding details (0/N)..." where N is the total task count from the skeleton
- After each `task_enriched`: "Adding details (X/N)..." where X increments
- After `generation_complete`: "Board ready!"
- After `generation_error`: "Generation failed"

The counter SHALL update in real-time as events arrive.

#### Scenario: Phase shows research in progress
- **WHEN** the user clicks "Generate Board" and `research_started` arrives with `query_count: 6`
- **THEN** the phase text reads "Researching (0/6)..."

#### Scenario: Phase shows research progress with query text
- **WHEN** `research_progress` arrives with `query: "Portugal visa requirements EU citizens"` and `queries_completed: 3`
- **THEN** the phase text reads "Researching (3/6)..." with subtitle "Searching: Portugal visa requirements EU citizens"

#### Scenario: Phase transitions from research to skeleton
- **WHEN** `research_complete` arrives
- **THEN** the phase text reads "Creating board structure..."

#### Scenario: Phase shows skeleton creation (no research)
- **WHEN** the user clicks "Generate Board" and no research events arrive (Tavily not configured), then receives `skeleton_ready`
- **THEN** the phase text transitions from "Analyzing your goal..." directly to "Adding details (0/N)..."

#### Scenario: Phase shows enrichment progress
- **WHEN** `skeleton_ready` has arrived with 15 tasks and 5 `task_enriched` events have been received
- **THEN** the phase text reads "Adding details (5/15)..."

#### Scenario: Phase shows completion
- **WHEN** the `generation_complete` event is received
- **THEN** the phase text reads "Board ready!"

#### Scenario: Phase shows error
- **WHEN** a `generation_error` event is received
- **THEN** the phase text reads "Generation failed"

### Requirement: SSE Client Hook
The system SHALL provide a React hook `useBoardGenerationStream` that manages the SSE connection lifecycle for board generation. The hook SHALL accept a `goalId` parameter and return the current generation state including: `phase` (string: "connecting" | "researching" | "skeleton" | "enriching" | "complete" | "error"), `boardTitle` (string | null), `tasks` (array of task objects with id, title, and isEnriched boolean), `enrichedCount` (number), `totalCount` (number), `boardId` (string | null), `error` (string | null), `researchProgress` (object | null with `queriesCompleted`, `totalQueries`, `currentQuery`, `totalResults` fields), and a `start()` function to initiate the connection. The hook SHALL handle connection cleanup on component unmount. The hook SHALL use a fetch-based SSE approach (not native `EventSource`) to support POST method and Authorization headers.

#### Scenario: Hook starts SSE connection
- **WHEN** `start()` is called on the hook
- **THEN** a POST fetch request with `Accept: text/event-stream` is made to `/api/goals/{goalId}/generate-board/stream` with the auth token

#### Scenario: Hook processes research events
- **WHEN** a `research_started` event is received followed by `research_progress` events
- **THEN** the hook updates `phase` to "researching" and populates `researchProgress` with query counts and current query text

#### Scenario: Hook processes skeleton event
- **WHEN** a `skeleton_ready` event is received
- **THEN** the hook updates `phase` to "enriching", sets `boardTitle`, populates `tasks` with skeleton data, and sets `totalCount`

#### Scenario: Hook processes enrichment event
- **WHEN** a `task_enriched` event is received
- **THEN** the hook marks the corresponding task as enriched and increments `enrichedCount`

#### Scenario: Hook cleans up on unmount
- **WHEN** the component using the hook unmounts
- **THEN** the SSE connection is aborted via `AbortController`

#### Scenario: Hook handles generation without research
- **WHEN** no research events are received and `skeleton_ready` arrives directly
- **THEN** the hook transitions from "connecting" to "enriching" phase (skipping "researching")
