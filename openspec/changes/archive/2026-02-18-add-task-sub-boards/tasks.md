## 1. Database Schema & Models

- [x] 1.1 Create Alembic migration: add nullable `parent_task_id` (UUID FK to task.id, ON DELETE CASCADE, unique index) to `board` table; make `goal_id` nullable; add CHECK constraint (`goal_id IS NOT NULL OR parent_task_id IS NOT NULL`)
- [x] 1.2 Update `Board` SQLModel in `app/domains/boards/models.py`: add `parent_task_id` field (nullable, FK to task.id), make `goal_id` optional, add relationship `parent_task` back-reference
- [x] 1.3 Update `Task` SQLModel: add optional `sub_board` relationship (back-reference from Board.parent_task_id)
- [x] 1.4 Verify migration runs cleanly on existing data (`alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head`)

## 2. Backend API Schemas

- [x] 2.1 Update `BoardResponse` in `schemas.py`: add `parent_task_id` (str | None), `parent_board` (object with `id`, `title` | None)
- [x] 2.2 Update `TaskResponse` in `schemas.py`: add `sub_board_id` (str | None), `sub_board_progress` (object with `task_count`, `completed_task_count` | None)
- [x] 2.3 Add `SubBoardQuestionsResponse` schema (list of questions, same format as goal questions)
- [x] 2.4 Add `SubBoardGenerateRequest` schema (answers array: `question_id`, `value`)

## 3. Backend Services & Repositories

- [x] 3.1 Add `is_root_board(board)` helper to `dag_utils.py` — checks `parent_task_id is None`
- [x] 3.2 Add `validate_nesting_depth(board)` to `dag_utils.py` — raises `NestingDepthError` if board has `parent_task_id`
- [x] 3.3 Update `board_repository.py`: add `get_sub_board_by_parent_task(task_id)`, `list_root_boards_for_user(user_id)`, `get_parent_board(board)` queries
- [x] 3.4 Update `board_service.py`: filter `list_boards` to root-only (`parent_task_id IS NULL`); add `create_sub_board(task, skeleton)` method; add `get_board_with_parent_info(board_id)` for breadcrumb data
- [x] 3.5 Update `board_service.py` response building: include `sub_board_id` and `sub_board_progress` per task, include `parent_task_id` and `parent_board` on board response
- [x] 3.6 Update `task_service.py` status transition: after transitioning a goal node to `done`, check if the board has `parent_task_id` and auto-complete the parent task
- [x] 3.7 Update `task_service.py` sub-board generation: add `generate_sub_board()` method that validates nesting, deletes subtasks, creates sub-board, auto-starts parent task
- [x] 3.8 Update ownership validation in `ownership.py`: support sub-board ownership checks (trace sub-board -> parent task -> board -> goal -> user)

## 4. AI Pipeline: Sub-Board Questions

- [x] 4.1 Create `app/domains/ai/prompts/sub_board_questions.py` — prompt for generating 2-4 focused decomposition questions
- [x] 4.2 Add `generate_sub_board_questions()` function to `app/domains/ai/service.py` — single LLM call with structured output, returns 2-4 questions
- [x] 4.3 Write unit test: prompt template validation (ID prefix, question count range, field types, language placeholders, rendering)

## 5. AI Pipeline: Sub-Board Skeleton & Enrichment

- [x] 5.1 Add sub-board skeleton prompt variant to `app/domains/ai/prompts/generate_board.py` — focused on decomposing a single task, 3-15 task range
- [x] 5.2 Add `generate_sub_board_stream()` async generator to `app/domains/ai/service.py` — resolves root goal context, invokes skeleton with adjusted params, reuses enrichment pipeline
- [x] 5.3 Write unit test: skeleton prompt importability and task range validation (3-15)

## 6. Backend API Endpoints

- [x] 6.1 Add `POST /api/tasks/:id/sub-board-questions` endpoint to `router.py` — validates ownership, root board, no existing sub-board, calls AI service
- [x] 6.2 Add `POST /api/tasks/:id/generate-sub-board` SSE endpoint to `router.py` — validates, streams generation events, persists sub-board
- [ ] 6.3 Write integration tests for sub-board question endpoint: happy path, already has sub-board (409), task on sub-board (422), wrong user (404) — blocked by pre-existing DB infra issue (pgvector)
- [ ] 6.4 Write integration tests for sub-board generation endpoint: happy path with SSE events, locked task (409), nesting limit (422) — blocked by pre-existing DB infra issue (pgvector)
- [ ] 6.5 Write integration test for completion propagation: mark sub-board goal node done -> verify parent task auto-completes — blocked by pre-existing DB infra issue (pgvector)

## 7. Frontend: API Client Regeneration

- [x] 7.1 Regenerate Orval API client from updated OpenAPI spec (new endpoints, updated response schemas)

## 8. Frontend: Breadcrumb Navigation

- [x] 8.1 Create `BreadcrumbNav` component in `frontend/src/features/board/components/BreadcrumbNav.tsx` — renders Home > Board Title (root) or Home > Parent Board > Task Title (sub-board)
- [x] 8.2 Update `boards.$boardId.tsx` route: replace hardcoded back button with `BreadcrumbNav`, pass `parent_board` data from board response
- [x] 8.3 Write component test for BreadcrumbNav: root board renders 2 segments, sub-board renders 3 segments, long titles truncated (6 tests)

## 9. Frontend: Task Node Sub-Board Visual Treatment

- [x] 9.1 Update `dagre-layout.ts`: pass `has_sub_board` and `sub_board_progress` in node data for tasks with `sub_board_id`
- [x] 9.2 Update `TaskNode` component: render layers icon + dashed purple border when `has_sub_board` is true; show sub-board progress instead of subtask count
- [x] 9.3 Update `DagView` node click handler: if task has `sub_board_id`, navigate to `/boards/:subBoardId` instead of opening detail panel
- [x] 9.4 Write component test for TaskNode: verify visual treatment when `has_sub_board` is true vs false (7 tests)

## 10. Frontend: Task Detail Panel Sub-Board Section

- [x] 10.1 Add "Sub-Board" section to `TaskDetailPanel`: when task has `sub_board_id`, show title, progress, and "Open Sub-Board" button (replaces subtasks section)
- [x] 10.2 Add "Expand to Board" button to `TaskDetailPanel`: visible when task has no sub-board and board is root-level; hidden on sub-board tasks
- [x] 10.3 Add confirmation dialog for "Expand to Board" when task has existing subtasks

## 11. Frontend: Inline Sub-Board Creation Flow

- [x] 11.1 Create `SubBoardCreationFlow` component: manages states (loading questions -> question form -> generating -> complete)
- [x] 11.2 Implement question form rendering in the flow: reuse `DynamicQuestionForm` field types (text, select, multiselect, number) in a compact panel layout
- [x] 11.3 Implement SSE streaming progress display during generation: show skeleton ready -> enrichment progress -> complete
- [x] 11.4 On completion: refresh board data (invalidate query), update task detail panel to show sub-board section
- [x] 11.5 Write component test: mock question API and generation mutations, verify flow transitions through all states (9 tests)

## 12. End-to-End Validation

- [ ] 12.1 Manual E2E test: create goal -> generate board -> expand task to sub-board (answer questions, generate) -> verify breadcrumb navigation -> complete sub-board -> verify parent task auto-completes
- [ ] 12.2 Verify home page board list does not show sub-boards
- [ ] 12.3 Verify deleting a parent task cascades to delete the sub-board
- [x] 12.4 Run full backend test suite (`pytest`) — pre-existing DB infra issue (pgvector extension); all non-DB unit tests pass (25/25)
- [x] 12.5 Run full frontend test suite (`vitest`) — 64/64 tests pass (10 test files)
- [x] 12.6 Run linters and type checks (`ruff check`, `tsc --noEmit`, `biome check`) — all pass
