## 1. Backend: Data Model & Migration

- [ ] 1.1 Add `Subtask` SQLModel to `backend/app/domains/boards/models.py` (id, task_id FK, title, completed, position varchar(50), created_at, updated_at)
- [ ] 1.2 Add `subtasks` relationship to `Task` model
- [ ] 1.3 Create Alembic migration: convert `column.position` and `task.position` from integer to varchar(50), convert existing data to fractional index strings, add `subtask` table with FK and index
- [ ] 1.4 Test migration against existing board data (up and down)

## 2. Backend: Schemas

- [ ] 2.1 Add `SubtaskResponse`, `SubtaskCreate`, `SubtaskUpdate` schemas to `boards/schemas.py`
- [ ] 2.2 Add `ColumnCreate`, `ColumnUpdate` schemas
- [ ] 2.3 Add `TaskCreate`, `TaskUpdate` schemas (TaskUpdate includes optional `column_id` for moves)
- [ ] 2.4 Add `BoardUpdate` schema (title only)
- [ ] 2.5 Add `BoardListResponse` schema (id, goal_id, title, goal_title, column_count, task_count, completed_task_count, created_at)
- [ ] 2.6 Update `ColumnResponse` and `TaskResponse` to use string position and include subtasks
- [ ] 2.7 Implement fractional indexing utility function in `boards/service.py` (generate_position_between, generate_position_after)

## 3. Backend: Service Layer

- [ ] 3.1 Add board list service function (query boards by user with summary stats)
- [ ] 3.2 Add board update service function
- [ ] 3.3 Add column CRUD service functions (create, update, delete with task migration)
- [ ] 3.4 Add task CRUD service functions (create, update including column move, delete with cascade subtasks)
- [ ] 3.5 Add subtask CRUD service functions (create, update, delete)
- [ ] 3.6 Add ownership validation helper (trace resource → user chain)
- [ ] 3.7 Update board persistence service to use fractional indexing for AI-generated boards

## 4. Backend: Router/Endpoints

- [ ] 4.1 Add `GET /api/boards` (list boards with summary)
- [ ] 4.2 Add `PATCH /api/boards/:id` (update board title)
- [ ] 4.3 Add `POST /api/boards/:id/columns` (create column)
- [ ] 4.4 Add `PATCH /api/columns/:id` (update column title/description/position)
- [ ] 4.5 Add `DELETE /api/columns/:id` (delete column, with target_column_id for task migration)
- [ ] 4.6 Add `POST /api/columns/:id/tasks` (create task)
- [ ] 4.7 Add `PATCH /api/tasks/:id` (update task fields, column move, position)
- [ ] 4.8 Add `DELETE /api/tasks/:id` (delete task + subtasks)
- [ ] 4.9 Add `POST /api/tasks/:id/subtasks` (create subtask)
- [ ] 4.10 Add `PATCH /api/subtasks/:id` (update subtask)
- [ ] 4.11 Add `DELETE /api/subtasks/:id` (delete subtask)
- [ ] 4.12 Update existing `GET /api/boards/:id` to include subtasks in response

## 5. Backend: Tests

- [ ] 5.1 Integration tests for column CRUD endpoints (create, update, delete, delete-with-migration)
- [ ] 5.2 Integration tests for task CRUD endpoints (create, update, move, delete)
- [ ] 5.3 Integration tests for subtask CRUD endpoints (create, toggle, delete)
- [ ] 5.4 Integration tests for board list endpoint
- [ ] 5.5 Integration tests for ownership validation (cross-user access returns 404)
- [ ] 5.6 Unit tests for fractional indexing utility functions

## 6. Frontend: Dependencies & API Generation

- [ ] 6.1 Install `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` via pnpm
- [ ] 6.2 Install `fractional-indexing` via pnpm
- [ ] 6.3 Regenerate Orval types and hooks from updated OpenAPI spec
- [ ] 6.4 Install toast notification library if not present (e.g., `sonner` or use Shadcn toast)

## 7. Frontend: Board Feature Module

- [ ] 7.1 Create `frontend/src/features/board/` directory with components/, hooks/, types.ts
- [ ] 7.2 Create `BoardView` component (main kanban layout, DnD context provider)
- [ ] 7.3 Create `BoardColumn` component (column header with inline edit, task list, add-task button)
- [ ] 7.4 Create `TaskCard` component (title, priority indicator, due date, subtask progress)
- [ ] 7.5 Create `TaskDetailPanel` component (slide-out panel with all editable fields + subtask checklist)
- [ ] 7.6 Create `SubtaskChecklist` component (checkbox list, inline add, delete)
- [ ] 7.7 Create `AddColumnButton` component (inline input pattern)
- [ ] 7.8 Create `AddTaskButton` component (inline input pattern)
- [ ] 7.9 Create `DeleteColumnDialog` component (confirmation with target column select)
- [ ] 7.10 Create `BoardSkeleton` component (loading state)

## 8. Frontend: Hooks & State Management

- [ ] 8.1 Create `useBoard` hook (wraps Orval query, board data access)
- [ ] 8.2 Create `useBoardList` hook (wraps Orval query for GET /api/boards)
- [ ] 8.3 Create `useMoveTask` hook (optimistic update for task drag-and-drop)
- [ ] 8.4 Create `useMoveColumn` hook (optimistic update for column drag-and-drop)
- [ ] 8.5 Create `useColumnMutations` hook (create, update, delete column with optimistic updates)
- [ ] 8.6 Create `useTaskMutations` hook (create, update, delete task with optimistic updates)
- [ ] 8.7 Create `useSubtaskMutations` hook (create, toggle, delete subtask with optimistic updates)
- [ ] 8.8 Create `useTaskDetailPanel` hook (open/close panel, URL search param sync)

## 9. Frontend: DnD Integration

- [ ] 9.1 Set up DnD context with pointer and keyboard sensors in BoardView
- [ ] 9.2 Implement sortable columns (horizontal SortableContext)
- [ ] 9.3 Implement sortable tasks within columns (vertical SortableContext per column)
- [ ] 9.4 Implement cross-column task movement with collision detection
- [ ] 9.5 Create drag overlay for task cards and columns
- [ ] 9.6 Compute fractional index positions on drop events

## 10. Frontend: Routes & Pages

- [ ] 10.1 Replace placeholder `boards.$boardId.tsx` with full kanban board page using BoardView
- [ ] 10.2 Add `task` search parameter to board route for task detail panel deep-linking
- [ ] 10.3 Update index page (`/`) to show board list with progress cards
- [ ] 10.4 Add board card component for home page list

## 11. Frontend: Tests

- [ ] 11.1 Component tests for TaskCard (renders metadata variants)
- [ ] 11.2 Component tests for BoardColumn (renders tasks, add-task input)
- [ ] 11.3 Component tests for TaskDetailPanel (field editing, subtask checklist)
- [ ] 11.4 Component tests for DeleteColumnDialog (shows task count, column picker)
- [ ] 11.5 Hook tests for optimistic update hooks (cache manipulation, rollback)

## 12. Integration & Validation

- [ ] 12.1 Run backend test suite — all tests pass
- [ ] 12.2 Run frontend type check (`tsc --noEmit`) — no errors
- [ ] 12.3 Run frontend lint (`biome check`) — no violations
- [ ] 12.4 Run frontend test suite (`vitest run`) — all tests pass
- [ ] 12.5 Manual smoke test: generate board → view kanban → drag tasks → add/edit/delete columns/tasks/subtasks
