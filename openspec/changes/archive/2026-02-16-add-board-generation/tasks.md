## 1. Backend — Boards Domain Foundation

- [x] 1.1 Create `backend/app/domains/boards/` package with `__init__.py`
- [x] 1.2 Define Board SQLModel in `boards/models.py` (id, goal_id unique FK, title, created_at, updated_at)
- [x] 1.3 Define Column SQLModel in `boards/models.py` (id, board_id FK, title, description, position, created_at, updated_at)
- [x] 1.4 Define Task SQLModel in `boards/models.py` (id, column_id FK, title, description, position, due_date nullable, priority nullable, estimated_minutes nullable, created_at, updated_at)
- [x] 1.5 Define SQLModel relationships: Board -> columns, Column -> tasks (with order_by position)
- [x] 1.6 Create Alembic migration for `board`, `column`, and `task` tables with FKs, unique constraint on `board.goal_id`, and indexes on `board.goal_id`, `column.board_id`, `task.column_id`
- [x] 1.7 Run migration against dev database and verify table structure
- [x] 1.8 Define Pydantic schemas in `boards/schemas.py`: `TaskResponse`, `ColumnResponse` (with nested tasks), `BoardResponse` (with nested columns), `BoardSummaryResponse`

## 2. Backend — AI Board Generation

- [x] 2.1 Define board generation AI output Pydantic models in `ai/schemas.py`: `BoardGenerationTaskOutput`, `BoardGenerationColumnOutput`, `BoardGenerationOutput`
- [x] 2.2 Write board generation system prompt in `ai/prompts/generate_board.py` — instruct AI to create goal-specific columns (not generic To Do/Doing/Done), actionable tasks, progressive metadata only when relevant, column count guided by complexity, task count 2-6 per column / max 30 total
- [x] 2.3 Implement board generation node in `ai/nodes/generate_board.py` using LangChain `ChatOpenAI` with `.with_structured_output(BoardGenerationOutput)`
- [x] 2.4 Add `board_generation` field to `GoalPipelineState` TypedDict in `ai/pipeline.py`
- [x] 2.5 Implement `generate_board(goal)` async function in `ai/service.py` — extracts context from goal's `ai_context`, invokes board generation node with retry logic, returns `BoardGenerationOutput`
- [ ] 2.6 Manual smoke test: call `generate_board` with 3-5 diverse goal contexts and verify output structure, column specificity, and progressive metadata

## 3. Backend — Board Persistence and Goal Status

- [x] 3.1 Implement board persistence in `boards/service.py`: `create_board_from_ai_output(goal_id, ai_output)` — creates Board, Column, and Task records in a single transaction
- [x] 3.2 Implement `get_board(board_id, user_id)` in `boards/service.py` — retrieves board with nested columns and tasks, validates ownership via goal.user_id
- [x] 3.3 Implement `get_board_by_goal(goal_id, user_id)` in `boards/service.py` — retrieves board by goal_id for convenience
- [x] 3.4 Add board generation orchestration to `goals/service.py` or `boards/service.py`: `generate_board_for_goal(goal_id, user_id)` — validates goal status is `answered`, transitions to `generating`, calls AI service, persists board, transitions to `active`, reverts to `answered` on failure

## 4. Backend — API Endpoints

- [x] 4.1 Implement `boards/router.py`: `POST /api/goals/{goal_id}/generate-board` — calls board generation orchestration, returns 201 with full board response
- [x] 4.2 Implement `boards/router.py`: `GET /api/boards/{board_id}` — calls get_board, returns board with nested columns and tasks
- [x] 4.3 Register boards router in `main.py` under `/api` prefix
- [x] 4.4 Regenerate OpenAPI spec and verify new endpoints appear

## 5. Backend — Testing

- [x] 5.1 Create test fixtures: sample AI board generation output, sample board/column/task data
- [x] 5.2 Write unit tests for Board, Column, Task model creation and relationships
- [x] 5.3 Write unit tests for board persistence service: successful creation, transaction rollback on failure
- [x] 5.4 Write AI output schema validation tests: verify `BoardGenerationOutput` against sample LLM responses (valid and invalid)
- [x] 5.5 Write integration tests for `POST /api/goals/:id/generate-board` — success case (mocked AI), wrong goal status (409), board already exists (409), wrong owner (404), unauthenticated (401)
- [x] 5.6 Write integration tests for `GET /api/boards/:id` — success with nested data, wrong owner (404), not found (404)
- [x] 5.7 Write integration tests for goal status transitions: `answered` -> `generating` -> `active`, revert to `answered` on failure
- [x] 5.8 Run full backend test suite, fix any failures

## 6. Frontend — Goal Summary Update

- [x] 6.1 Run Orval codegen to generate TypeScript types and React Query hooks for new board endpoints
- [x] 6.2 Verify generated types match backend schemas (BoardResponse, ColumnResponse, TaskResponse)
- [x] 6.3 Enable "Generate Board" button in `GoalSummary` component — wire to `POST /goals/:id/generate-board` mutation
- [x] 6.4 Add loading state during board generation (spinner, "Generating your board..." message)
- [x] 6.5 Add error handling for generation failure with "Try Again" retry button
- [x] 6.6 On success, redirect to `/boards/:id` route (route may show a placeholder until board view proposal is implemented)

## 7. End-to-End Validation

- [ ] 7.1 Manual E2E test: create goal -> answer questions -> click Generate Board -> verify board created with custom columns and tasks in database
- [ ] 7.2 Manual E2E test: verify goal status transitions from `answered` -> `generating` -> `active`
- [ ] 7.3 Manual E2E test: AI timeout/error -> goal reverts to `answered` -> retry succeeds
- [ ] 7.4 Test with diverse goal types: personal (move), professional (launch product), creative (write novel), learning (learn language), health (train for marathon)
- [ ] 7.5 Verify generated boards have goal-specific columns (not generic To Do/Doing/Done) for each goal type
- [ ] 7.6 Verify progressive metadata is applied selectively (not all tasks have all fields, not all tasks are missing all fields)
- [ ] 7.7 Verify Docker Compose works with new database tables
- [x] 7.8 Verify CI pipeline passes with new code (linting, type checking, tests)

**Parallelizable work:**
- Tasks 1.x and 2.1-2.2 can run in parallel (boards domain foundation and AI schema/prompt work)
- Tasks 5.x tests can be written alongside 3.x-4.x implementation
- Task 6.x (frontend) can start once 4.4 is done (needs OpenAPI spec from registered endpoints)

**Dependencies:**
- 2.3-2.5 depend on 2.1-2.2 (node needs schemas and prompt)
- 3.x depends on 1.x and 2.x (persistence needs models and AI service)
- 4.x depends on 3.x (endpoints need service layer)
- 5.x depends on 3.x and 4.x (tests need services and endpoints)
- 6.x depends on 4.4 (frontend codegen needs OpenAPI spec)
- 7.x depends on all previous sections
