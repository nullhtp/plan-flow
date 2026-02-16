# Change: Add Kanban Board UI with Full Editing

## Why
Users can generate boards via the AI pipeline, but the board view is a placeholder that only shows the title and counts. Users need to view their boards as interactive kanban layouts and fully edit them: drag-and-drop tasks between columns, reorder columns and tasks, add/remove/edit columns and tasks, manage subtasks, and view/edit task details in a side panel.

## What Changes
- **New frontend feature module** (`features/board/`) with kanban board components, task detail side panel, and drag-and-drop interactions using `@dnd-kit`
- **New backend CRUD endpoints** for columns, tasks, and subtasks (create, read, update, delete, reorder/move)
- **New Subtask data model** — database model, migration, and schemas for checklist items within tasks
- **Fractional indexing** for column and task positions — replaces current integer positions to avoid renumbering on reorder
- **Database migration** to convert existing integer positions to fractional index strings and add the subtask table
- **Optimistic updates** via React Query for all drag-and-drop and editing operations
- **Board list on home page** — authenticated index page shows all user boards with title, progress, and goal summary
- **Replace placeholder board route** with full kanban board view
- **Orval regeneration** for new backend endpoints

## Impact
- Affected specs: `board-management` (MODIFIED: position strategy, ADDED: column/task/subtask CRUD endpoints + subtask model), `board-ui` (NEW capability)
- Affected code:
  - `backend/app/domains/boards/` — models, schemas, router, service (significant additions)
  - `backend/migrations/` — new Alembic migration for fractional indexing + subtask table
  - `frontend/src/features/board/` — new feature module (components, hooks, types)
  - `frontend/src/routes/boards.$boardId.tsx` — replace placeholder with kanban view
  - `frontend/src/routes/index.tsx` — add board list
  - `frontend/src/api/` — Orval regeneration for new endpoints
  - `frontend/package.json` — add `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`, `fractional-indexing`
