## 1. Backend Data Model & Migration

- [x] 1.1 Create `TaskDependency` SQLModel in `app/domains/boards/models.py` with `dependent_task_id` and `dependency_task_id` FKs, unique constraint on the pair
- [x] 1.2 Modify `Task` model: replace `column_id` FK with `board_id` FK, add `status` field (varchar, default `not_started`), add `is_goal_node` field (boolean, default false), remove `position` field
- [x] 1.3 Remove `BoardColumn` model from `app/domains/boards/models.py`
- [x] 1.4 Update `Board` model: remove `columns` relationship, add `tasks` relationship
- [x] 1.5 Create Alembic migration: drop `subtask`, `task`, `board_column` tables (cascade), recreate `board`, `task`, `task_dependency`, `subtask` with new schema
- [x] 1.6 Implement DAG validation utility in `app/domains/boards/dag_utils.py` (topological sort, cycle detection, single goal node validation)
- [x] 1.7 Write unit tests for DAG validation utility (valid DAG, cycles, self-dependency, missing/multiple goal nodes, goal node with dependents)

## 2. Backend Schemas & API

- [x] 2.1 Update Pydantic schemas in `app/domains/boards/schemas.py`: remove column schemas, add `TaskDependencyResponse`, update `TaskResponse` (add `status`, `is_goal_node`, `dependency_ids`, `dependent_ids`, `is_locked`; remove `column_id`, `position`), update `BoardResponse` (add `tasks`, `edges`, `is_completed`; remove `columns`)
- [x] 2.2 Update `TaskCreate` and `TaskUpdate` schemas: `TaskCreate` takes `board_id` context, `TaskUpdate` adds `status` field, remove `column_id` and `position`
- [x] 2.3 Update `BoardListResponse`: remove `column_count`, change `completed_task_count` to count tasks with status `done`

## 3. Backend Service Layer

- [x] 3.1 Rewrite board persistence service (`create_board_from_ai_output`) to create Board + Tasks + TaskDependencies in one transaction (no columns)
- [x] 3.2 Add DAG validation call in persistence service before committing (cycle detection + single goal node + goal node is sink)
- [x] 3.3 Implement task status transition validation: `not_started` -> `in_progress` requires all deps `done`; `in_progress` -> `done` allowed; `not_started` -> `done` rejected
- [x] 3.4 Implement `is_locked` computation in get_board query
- [x] 3.5 Implement `is_completed` computation (goal node has status `done`) in get_board query
- [x] 3.6 Implement dependency query helpers: `get_task_dependencies`, `get_task_dependents`, `are_dependencies_met`
- [x] 3.7 Update delete task service to cascade delete dependency edges

## 4. Backend Router

- [x] 4.1 Remove all column endpoints: `POST /api/boards/:id/columns`, `PATCH /api/columns/:id`, `DELETE /api/columns/:id`
- [x] 4.2 Update `POST /api/boards/:id/tasks` endpoint (create task on board, not column)
- [x] 4.3 Update `PATCH /api/tasks/:id` to handle `status` field with transition validation
- [x] 4.4 Update `GET /api/boards/:id` to return tasks with dependencies, `is_locked`, and `is_completed`
- [x] 4.5 Update `GET /api/boards` (list) to compute `completed_task_count` from status field
- [x] 4.6 Update `POST /api/goals/:id/generate-board` to return new response format

## 5. Backend Tests

- [x] 5.1 Write integration tests for board generation with dependencies
- [x] 5.2 Write integration tests for task status transitions (valid and invalid)
- [x] 5.3 Write integration tests for task deletion with dependency cascade
- [x] 5.4 Write integration tests for `is_locked` and `is_completed` computations
- [x] 5.5 Update existing board/task tests for new schema (remove column tests)

## 6. AI Pipeline Changes

- [x] 6.1 Update `BoardGenerationOutput` Pydantic schema in `app/domains/ai/schemas.py`: flat task list with `id`, `depends_on` array, and `is_goal_node` boolean per task (no columns)
- [x] 6.2 Update board generation prompt in `app/domains/ai/prompts/generate_board.py` to instruct AI to produce dependency edges, parallel paths, convergence nodes, a single final goal node, and valid DAG structure
- [x] 6.3 Add DAG validation to `generate_board` AI service function (retry on cycles)
- [x] 6.4 Update `generate_board` node in `app/domains/ai/nodes/generate_board.py` to use new output schema
- [x] 6.5 Write tests: validate AI output schema, test cycle detection retry, test dependency structure

## 7. Frontend: Install Dependencies & Cleanup

- [x] 7.1 Install `@xyflow/react` and `dagre` packages; install `canvas-confetti` for celebration
- [x] 7.2 Remove `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` packages
- [x] 7.3 Remove `fractional-indexing` package (no longer needed for task/column ordering)
- [x] 7.4 Regenerate Orval API client from updated backend OpenAPI spec

## 8. Frontend: DAG Graph View

- [x] 8.1 Create `DagView` component using React Flow with dagre auto-layout (replaces `BoardView`)
- [x] 8.2 Create custom `TaskNode` component for React Flow (renders task info, status indicator, lock icon for locked tasks)
- [x] 8.2a Create custom `GoalNode` component for React Flow (larger node, accent border, progress summary, distinct visual style for the final goal task)
- [x] 8.3 Implement dagre layout utility to convert board tasks + edges into React Flow nodes/edges with computed positions
- [x] 8.4 Add pan/zoom controls and minimap to the graph view
- [x] 8.5 Style dependency edges (arrows from prerequisite to dependent, dimmed for locked paths)

## 9. Frontend: Task Interaction

- [x] 9.1 Implement status toggle on task nodes (click to cycle not_started -> in_progress -> done, disabled when locked)
- [x] 9.2 Update `TaskDetailPanel` to show status selector, dependencies section (read-only list), and unlocks section (read-only list); remove column selector
- [x] 9.3 Implement locked task tooltip showing prerequisite task names
- [x] 9.4 Add optimistic updates for status changes with rollback on error

## 10. Frontend: Board Route & Home Page

- [x] 10.1 Update board detail route (`/boards/$boardId`) to render `DagView` instead of `BoardView`
- [x] 10.2 Update `BoardCard` component on home page: remove column count, show task completion ratio from status-based counting
- [x] 10.3 Update board loading state component (replace kanban skeleton with graph loading indicator)

## 11. Frontend: Celebration & Polish

- [x] 11.1 Implement goal completion celebration: detect goal node status `done` / `is_completed` from API response, trigger confetti animation and "Goal Complete!" overlay
- [ ] 11.2 Add unlock animation: when a task transitions from locked to unlocked, animate the lock icon removal and color change
- [x] 11.3 Remove all kanban-related components: `BoardView`, `BoardColumn`, `AddColumnButton`, `AddTaskButton`, `DeleteColumnDialog`, and associated hooks (`use-move-task`, `use-move-column`, `use-column-mutations`)

## 12. Frontend Tests

- [ ] 12.1 Write component tests for `TaskNode` and `GoalNode` (status display, lock state, metadata rendering, goal node progress summary)
- [ ] 12.2 Write component tests for status toggle behavior (unlocked cycles, locked disabled)
- [ ] 12.3 Write component tests for celebration trigger
- [x] 12.4 Remove obsolete kanban component tests (`task-card.test.tsx`, `delete-column-dialog.test.tsx`)

## 13. End-to-End Validation

- [ ] 13.1 Test full flow: create goal -> answer questions -> generate DAG board -> view graph -> complete tasks -> celebration
- [x] 13.2 Verify API documentation (OpenAPI spec) reflects all changes
- [x] 13.3 Run full backend test suite, fix any regressions
- [x] 13.4 Run full frontend test suite, fix any regressions
