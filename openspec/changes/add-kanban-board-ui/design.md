## Context

The AI pipeline generates boards with columns and tasks, but the frontend is a placeholder. This change builds the full interactive kanban board UI with drag-and-drop, inline editing, a task detail side panel, subtask management, and full CRUD API endpoints. It spans both frontend and backend, introduces new dependencies (`@dnd-kit`, `fractional-indexing`), changes the position storage strategy, and adds a new database table (subtasks).

**Stakeholders:** Solo developer. No multi-user collaboration concerns.

## Goals / Non-Goals

**Goals:**
- Fully interactive kanban board: view columns horizontally, tasks as cards
- Drag-and-drop for tasks (within and between columns) and columns (reorder)
- Full CRUD for columns, tasks, and subtasks via REST API
- Task detail side panel for editing all fields (title, description, due date, priority, time estimate, subtasks)
- Optimistic updates for all mutations (instant UI, rollback on error)
- Board list on home page with progress indicators
- Fractional indexing for position management

**Non-Goals:**
- Keyboard shortcuts (deferred)
- Real-time collaboration / WebSocket sync (single-user MVP)
- Task status/completed field (column position IS status)
- Board settings, themes, or customization
- Search/filter within a board
- Undo/redo beyond optimistic rollback

## Decisions

### 1. Drag-and-Drop: `@dnd-kit`

**Decision:** Use `@dnd-kit/core` + `@dnd-kit/sortable` + `@dnd-kit/utilities`.

**Rationale:** Modular, tree-shakeable, actively maintained. Built-in keyboard and pointer sensors. Supports both vertical (tasks within column) and horizontal (columns) sorting with collision detection strategies. The `SortableContext` + `useSortable` pattern maps cleanly to our column/task hierarchy.

**Alternatives considered:**
- `@hello-pangea/dnd` — simpler API but less flexible for nested sortable contexts. Community fork of archived `react-beautiful-dnd`.

### 2. Position Strategy: Fractional Indexing

**Decision:** Replace integer `position` columns with string-based fractional index keys. Use the `fractional-indexing` npm library on frontend and a Python port (`fractional_indexing` or inline implementation) on backend.

**Rationale:** Integer positions require renumbering all siblings on every insert/reorder. Fractional indexing generates a string key between any two existing keys without modifying other rows. This is critical for optimistic updates — the client can compute the new position locally without knowing the full sibling list.

**Migration:** Alembic migration converts existing integer positions to fractional index strings (e.g., 0→"a0", 1→"a1", 2→"a2"). Column type changes from `integer` to `varchar(50)`. Sorting remains `ORDER BY position ASC` since fractional index strings sort lexicographically.

**Alternatives considered:**
- Gap-based integers (e.g., 1000, 2000) — simpler but requires periodic rebalancing and doesn't compose well with optimistic updates
- Keep simple integers — too many DB writes per reorder, conflicts with optimistic update strategy

### 3. Optimistic Updates via React Query

**Decision:** All board mutations (drag-drop, add/edit/delete column/task/subtask) use React Query's `onMutate` → optimistic cache update → `onError` rollback → `onSettled` invalidate pattern.

**Rationale:** Drag-and-drop must feel instant. Waiting for server round-trips creates noticeable lag. React Query's cache manipulation provides a clean rollback mechanism if the server rejects the change.

**Pattern:**
```
onMutate: snapshot cache → update cache optimistically
onError: restore snapshot
onSettled: invalidate query to re-sync
```

### 4. Task Detail: Right Side Panel

**Decision:** Clicking a task card opens a slide-out panel on the right (approximately 400-480px wide). The board remains visible and scrollable behind it. Panel contains editable fields: title, description (textarea), due date (date picker), priority (select), time estimate (number input), and subtask checklist.

**Rationale:** Side panel keeps the board context visible, allowing users to see where the task sits relative to other tasks/columns. Modals obscure the board.

**Implementation:** The panel state is managed via URL search params (`?task=<taskId>`) so that direct linking to a task detail is possible and browser back/forward works naturally.

### 5. Subtask Model

**Decision:** Add a `Subtask` table: `id` (UUID PK), `task_id` (FK to Task), `title` (string), `completed` (boolean, default false), `position` (varchar, fractional index), `created_at`, `updated_at`.

**Rationale:** Subtasks are simple checklist items — title + completed toggle. Position uses fractional indexing for consistent reordering. No nesting beyond one level (no sub-subtasks).

### 6. Backend CRUD Endpoint Design

**Decision:** All CRUD endpoints live in `boards/router.py` under the existing board domain. No separate `columns/` or `tasks/` domain directories.

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| `PATCH` | `/api/boards/:id` | Update board title |
| `POST` | `/api/boards/:id/columns` | Create column |
| `PATCH` | `/api/columns/:id` | Update column (title, position) |
| `DELETE` | `/api/columns/:id` | Delete column (move tasks to target column) |
| `POST` | `/api/columns/:id/tasks` | Create task |
| `PATCH` | `/api/tasks/:id` | Update task (any field, including column_id for moves and position for reorder) |
| `DELETE` | `/api/tasks/:id` | Delete task |
| `POST` | `/api/tasks/:id/subtasks` | Create subtask |
| `PATCH` | `/api/subtasks/:id` | Update subtask (title, completed, position) |
| `DELETE` | `/api/subtasks/:id` | Delete subtask |

**Rationale:** Flat REST routes (not deeply nested) keep URLs short and make ownership validation straightforward. Each endpoint validates that the resource belongs to the authenticated user by tracing the ownership chain (subtask → task → column → board → goal → user).

### 7. Column Deletion with Task Migration

**Decision:** `DELETE /api/columns/:id` requires a `target_column_id` query parameter when the column has tasks. Tasks are moved to the target column (appended at the end with new fractional index positions) before the column is deleted. If the column is empty, `target_column_id` is optional.

**Rationale:** User chose "confirm + move tasks" pattern. This prevents accidental data loss. The frontend shows a confirmation dialog listing the task count and a dropdown to select the destination column.

### 8. Board List on Home Page

**Decision:** Add `GET /api/boards` endpoint returning all boards for the authenticated user with summary data (title, goal title, column count, total tasks, completed-column task count). The frontend index page renders a card grid.

**Rationale:** Users need a way to navigate to existing boards. The current index page only has a "New Goal" button. Progress is approximated by counting tasks in the last column (assumed to be a "done" column) vs. total tasks — this is a simple heuristic without requiring an explicit task status field.

## Risks / Trade-offs

- **Fractional indexing migration** — existing boards with integer positions must be migrated. Risk: if any board has many tasks, the migration must handle them correctly. Mitigation: migration is a simple data transformation (int → string), tested against existing data before deployment.
- **Optimistic update complexity** — cache manipulation for nested data (board → columns → tasks) can be error-prone. Mitigation: extract optimistic update logic into reusable utility functions. Invalidate full board query on `onSettled` as safety net.
- **@dnd-kit learning curve** — the multi-container sortable pattern (tasks moving between columns) requires careful collision detection setup. Mitigation: follow dnd-kit's documented multi-container example.
- **Progress heuristic** — counting tasks in the last column as "completed" is imprecise (user may rename/reorder columns). Acceptable for MVP; can improve later with explicit column types or task status.

## Open Questions

- None — all decisions made via user input.
