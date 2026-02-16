## 1. Backend: Data Model & Migration

- [x] 1.1 Add `Subtask` SQLModel to `backend/app/domains/boards/models.py` (id, task_id FK, title, completed, position varchar(50), created_at, updated_at)
- [x] 1.2 Add `subtasks` relationship to `Task` model
- [x] 1.3 Create Alembic migration: convert `column.position` and `task.position` from integer to varchar(50), convert existing data to fractional index strings, add `subtask` table with FK and index
- [x] 1.4 Test migration against existing board data (up and down)

## 2. Backend: Schemas

- [x] 2.1 Add `SubtaskResponse`, `SubtaskCreate`, `SubtaskUpdate` schemas to `boards/schemas.py`
- [x] 2.2 Add `ColumnCreate`, `ColumnUpdate` schemas
- [x] 2.3 Add `TaskCreate`, `TaskUpdate` schemas (TaskUpdate includes optional `column_id` for moves)
- [x] 2.4 Add `BoardUpdate` schema (title only)
- [x] 2.5 Add `BoardListResponse` schema (id, goal_id, title, goal_title, column_count, task_count, completed_task_count, created_at)
- [x] 2.6 Update `ColumnResponse` and `TaskResponse` to use string position and include subtasks
- [x] 2.7 Implement fractional indexing utility function in `boards/service.py` (generate_position_between, generate_position_after)

## 3. Backend: Service Layer

- [x] 3.1 Add board list service function (query boards by user with summary stats)
- [x] 3.2 Add board update service function
- [x] 3.3 Add column CRUD service functions (create, update, delete with task migration)
- [x] 3.4 Add task CRUD service functions (create, update including column move, delete with cascade subtasks)
- [x] 3.5 Add subtask CRUD service functions (create, update, delete)
- [x] 3.6 Add ownership validation helper (trace resource → user chain)
- [x] 3.7 Update board persistence service to use fractional indexing for AI-generated boards

## 4. Backend: Router/Endpoints

- [x] 4.1 Add `GET /api/boards` (list boards with summary)
- [x] 4.2 Add `PATCH /api/boards/:id` (update board title)
- [x] 4.3 Add `POST /api/boards/:id/columns` (create column)
- [x] 4.4 Add `PATCH /api/columns/:id` (update column title/description/position)
- [x] 4.5 Add `DELETE /api/columns/:id` (delete column, with target_column_id for task migration)
- [x] 4.6 Add `POST /api/columns/:id/tasks` (create task)
- [x] 4.7 Add `PATCH /api/tasks/:id` (update task fields, column move, position)
- [x] 4.8 Add `DELETE /api/tasks/:id` (delete task + subtasks)
- [x] 4.9 Add `POST /api/tasks/:id/subtasks` (create subtask)
- [x] 4.10 Add `PATCH /api/subtasks/:id` (update subtask)
- [x] 4.11 Add `DELETE /api/subtasks/:id` (delete subtask)
- [x] 4.12 Update existing `GET /api/boards/:id` to include subtasks in response

## 5. Backend: Tests

- [x] 5.1 Integration tests for column CRUD endpoints (create, update, delete, delete-with-migration)
- [x] 5.2 Integration tests for task CRUD endpoints (create, update, move, delete)
- [x] 5.3 Integration tests for subtask CRUD endpoints (create, toggle, delete)
- [x] 5.4 Integration tests for board list endpoint
- [x] 5.5 Integration tests for ownership validation (cross-user access returns 404)
- [x] 5.6 Unit tests for fractional indexing utility functions

## 6. Frontend: Dependencies & API Generation

- [x] 6.1 Install `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` via pnpm
- [x] 6.2 Install `fractional-indexing` via pnpm
- [x] 6.3 Regenerate Orval types and hooks from updated OpenAPI spec
- [x] 6.4 Install toast notification library if not present (e.g., `sonner` or use Shadcn toast)

## 7. Frontend: Board Feature Module

- [x] 7.1 Create `frontend/src/features/board/` directory with components/, hooks/, types.ts
- [x] 7.2 Create `BoardView` component (main kanban layout, DnD context provider)
- [x] 7.3 Create `BoardColumn` component (column header with inline edit, task list, add-task button)
- [x] 7.4 Create `TaskCard` component (title, priority indicator, due date, subtask progress)
- [x] 7.5 Create `TaskDetailPanel` component (slide-out panel with all editable fields + subtask checklist)
- [x] 7.6 Create `SubtaskChecklist` component (checkbox list, inline add, delete)
- [x] 7.7 Create `AddColumnButton` component (inline input pattern)
- [x] 7.8 Create `AddTaskButton` component (inline input pattern)
- [x] 7.9 Create `DeleteColumnDialog` component (confirmation with target column select)
- [x] 7.10 Create `BoardSkeleton` component (loading state)

## 8. Frontend: Hooks & State Management

- [x] 8.1 Create `useBoard` hook (wraps Orval query, board data access)
- [x] 8.2 Create `useBoardList` hook (wraps Orval query for GET /api/boards)
- [x] 8.3 Create `useMoveTask` hook (optimistic update for task drag-and-drop)
- [x] 8.4 Create `useMoveColumn` hook (optimistic update for column drag-and-drop)
- [x] 8.5 Create `useColumnMutations` hook (create, update, delete column with optimistic updates)
- [x] 8.6 Create `useTaskMutations` hook (create, update, delete task with optimistic updates)
- [x] 8.7 Create `useSubtaskMutations` hook (create, toggle, delete subtask with optimistic updates)
- [x] 8.8 Create `useTaskDetailPanel` hook (open/close panel, URL search param sync)

## 9. Frontend: DnD Integration

- [x] 9.1 Set up DnD context with pointer and keyboard sensors in BoardView
- [x] 9.2 Implement sortable columns (horizontal SortableContext)
- [x] 9.3 Implement sortable tasks within columns (vertical SortableContext per column)
- [x] 9.4 Implement cross-column task movement with collision detection
- [x] 9.5 Create drag overlay for task cards and columns
- [x] 9.6 Compute fractional index positions on drop events

## 10. Frontend: Routes & Pages

- [x] 10.1 Replace placeholder `boards.$boardId.tsx` with full kanban board page using BoardView
- [x] 10.2 Add `task` search parameter to board route for task detail panel deep-linking
- [x] 10.3 Update index page (`/`) to show board list with progress cards
- [x] 10.4 Add board card component for home page list

## 11. Frontend: Tests

- [x] 11.1 Component tests for TaskCard (renders metadata variants)
- [x] 11.2 Component tests for BoardColumn (renders tasks, add-task input)
- [x] 11.3 Component tests for TaskDetailPanel (field editing, subtask checklist)
- [x] 11.4 Component tests for DeleteColumnDialog (shows task count, column picker)
- [x] 11.5 Hook tests for optimistic update hooks (cache manipulation, rollback)

## 12. Integration & Validation

- [x] 12.1 Run backend test suite — all tests pass
- [x] 12.2 Run frontend type check (`tsc --noEmit`) — no errors
- [x] 12.3 Run frontend lint (`biome check`) — no violations
- [x] 12.4 Run frontend test suite (`vitest run`) — all tests pass
- [x] 12.5 Manual smoke test: generate board → view kanban → drag tasks → add/edit/delete columns/tasks/subtasks
