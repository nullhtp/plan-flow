# Change: Replace Kanban Board with DAG Task Graph

## Why
The current kanban board (columns + drag-and-drop) does not express task dependencies — users cannot see which tasks block others or which can be done in parallel. Replacing the board with a directed acyclic graph (DAG) gives users a game-like experience where completing tasks unlocks dependent tasks, making progress visible and motivating.

## What Changes
- **BREAKING** — Remove kanban column-based board UI entirely (no dual view)
- **BREAKING** — Remove Column data model and all column CRUD endpoints
- **BREAKING** — Drop all existing boards (users regenerate as DAGs)
- Add `TaskDependency` junction table to model directed edges between tasks
- Add `status` field to Task (`not_started`, `in_progress`, `done`) replacing column-based progress tracking
- Modify AI board generation to produce a flat task list with dependency edges instead of column-grouped tasks
- AI generates convergence nodes where parallel paths merge into shared milestone tasks
- AI generates exactly one final "goal node" per board — the single sink of the DAG representing the user's original goal, depending on all leaf tasks
- Add `is_goal_node` boolean field to Task model
- Replace the React kanban view with a React Flow-based DAG visualization
- Goal node rendered with distinct visual style (larger, accent border, progress summary)
- Locked tasks (unmet prerequisites) appear grayed out with a lock icon
- Completing the goal node triggers a celebration animation
- Auto-layout via dagre algorithm (no manual node repositioning)
- AI-only dependency generation for MVP (manual editing deferred to future proposal)

## Impact
- Affected specs: `board-management`, `board-ui`, `ai-pipeline`, new `task-dag` capability
- Affected code:
  - Backend: `domains/boards/models.py`, `schemas.py`, `router.py`, `service.py`, Alembic migrations
  - Backend: `domains/ai/nodes/generate_board.py`, `prompts/generate_board.py`, `schemas.py`, `pipeline.py`
  - Frontend: `features/board/` (all components, hooks, types rewritten)
  - Frontend: `package.json` (add `@xyflow/react`, `dagre`; remove `@dnd-kit/*`)
  - Frontend: `api/` (Orval regeneration after schema changes)
- Migration: Existing boards and columns are dropped. Users regenerate boards as DAGs.
