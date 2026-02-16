## Context

PlanFlow currently uses a kanban board (columns + tasks + drag-and-drop) to represent generated plans. The user wants a game-like DAG (directed acyclic graph) where tasks are nodes, dependencies are edges, and completing a task "unlocks" its dependents. This is a cross-cutting change spanning the data model, AI generation pipeline, API, and entire frontend board UI.

Key stakeholders: solo developer, end users of the SaaS.

## Goals / Non-Goals

### Goals
- Replace the kanban board with a DAG-based task graph view
- AI generates task dependency edges during board generation
- Locked tasks (unmet prerequisites) are visually distinct (grayed + lock icon)
- Task status (`not_started` / `in_progress` / `done`) replaces column-based progress
- Parallel task paths are supported (tasks with no dependency relationship)
- Auto-layout via dagre algorithm
- Convergence nodes where parallel paths merge into shared milestones
- Final goal node at the bottom of the DAG representing the user's original goal
- Completion celebration when the goal node is completed
- Clean removal of column-based data model and UI

### Non-Goals
- Manual dependency editing by users (deferred to a future proposal)
- Keeping kanban as a secondary/fallback view
- Migrating existing boards (they are dropped; users regenerate)
- Subtask dependency tracking (subtasks remain simple checklists)
- Custom node positioning (auto-layout only)
- Weighted edges or complex dependency types (e.g., "soft" vs "hard" dependency)

## Decisions

### 1. Data Model: TaskDependency junction table
- **Decision**: Add a `task_dependency` table with `dependent_task_id` (the blocked task) and `dependency_task_id` (the prerequisite). This is a many-to-many self-referential relationship on Task.
- **Why**: Clean relational model, easy to query "what blocks this task?" and "what does this task unlock?". Supports arbitrary DAG topologies.
- **Alternatives considered**:
  - JSON array of dependency IDs on Task: simpler but harder to query, no FK integrity.
  - Adjacency list with `parent_id` on Task: only supports tree structures, not DAGs.

### 2. Remove Column model entirely
- **Decision**: Drop the `board_column` table and all column CRUD endpoints. Tasks belong directly to a Board (new `board_id` FK on Task, replacing `column_id`).
- **Why**: Columns represent kanban phases. In a DAG, task ordering comes from dependency edges, not columns. Keeping columns as unused scaffolding adds confusion.
- **Alternatives considered**:
  - Keep columns as "phases" mapped to visual groups: adds complexity, the DAG layout engine handles grouping better via topology.
  - Keep columns in DB but hide from UI: technical debt, schema confusion.

### 3. Task status field
- **Decision**: Add `status` enum field (`not_started`, `in_progress`, `done`) to the Task model. Default: `not_started`.
- **Why**: Without columns, we need an explicit status. Three states match common task workflows and the game-like unlock mechanic. A task can only transition to `in_progress` or `done` if all its dependencies are `done`.
- **Alternatives considered**:
  - Boolean `completed`: too simple, no "in progress" state.
  - Integer progress percentage: overcomplicated for MVP.

### 4. React Flow for DAG visualization
- **Decision**: Use `@xyflow/react` (React Flow v12) with custom task nodes and `dagre` for auto-layout.
- **Why**: React Flow is the most popular React graph library, has excellent custom node support, built-in pan/zoom/minimap, and active maintenance. Dagre is the standard hierarchical graph layout algorithm.
- **Alternatives considered**:
  - D3.js: too low-level, significant effort to build interactive nodes.
  - Cytoscape.js: powerful but less React-native, heavier bundle.
  - Elk.js: better layouts but more complex API; dagre is sufficient for task DAGs.

### 5. AI generates dependencies as part of board generation
- **Decision**: Modify the board generation prompt and output schema to produce a flat list of tasks with a `depends_on` array per task (list of task indices). The AI determines the dependency graph based on logical task ordering.
- **Why**: The AI already understands task relationships (it currently orders tasks within columns by execution order). Producing explicit dependency edges is a natural extension.
- **Constraints**: The output must form a valid DAG (no cycles). Validation will be added post-generation.

### 6. Drop existing boards, no migration
- **Decision**: Add a migration that drops all board/column/task/subtask data and restructures the schema. Users regenerate boards as DAGs.
- **Why**: The schema change is fundamental (removing columns, adding dependencies, adding status). Migrating existing data would require AI re-analysis of each board, which is complex and error-prone.

### 7. Auto-layout only (no manual node positioning)
- **Decision**: Dagre computes node positions on every render. No position data is stored in the database.
- **Why**: Simpler implementation, consistent layout, no need for position persistence. Users focus on completing tasks, not arranging a graph.
- **Future**: If users want custom layouts, we can add `x`/`y` fields to Task later.

### 8. Convergence nodes (merge points)
- **Decision**: The AI generates convergence nodes — tasks that depend on multiple parallel paths. These are regular tasks with multiple entries in `depends_on`. No special data model treatment; the DAG topology naturally supports fan-in.
- **Why**: Multiple independent work streams (e.g., housing search and job search in a relocation) logically converge at milestones (e.g., "Finalize relocation timeline"). Dagre layout naturally renders fan-in patterns by positioning upstream nodes side by side with edges converging below.
- **Alternatives considered**:
  - Explicit "milestone" task type: adds complexity with no clear benefit — a regular task with multiple dependencies achieves the same result.

### 9. Final goal node as DAG sink
- **Decision**: The AI always generates exactly one task with `is_goal_node: true`. This task represents the user's original goal (e.g., "Complete: Relocate to Lisbon"), depends on all leaf tasks, and is the single sink of the DAG (nothing depends on it). The celebration triggers when this node is completed, not when all tasks are done.
- **Why**: Gives the DAG a clear visual endpoint — a single "finish line" node at the bottom of the graph. Makes progress tangible: the user works through the graph toward one clear destination. Also provides a natural trigger for the celebration animation.
- **Data model**: Boolean `is_goal_node` field on Task (default false). Exactly one per board, enforced at persistence time.
- **Alternatives considered**:
  - No explicit goal node, detect "all tasks done": works but lacks visual focus. The graph has multiple leaf nodes with no clear endpoint.
  - Separate GoalNode model: over-engineered — it's just a task with a flag.

### 10. Lock enforcement
- **Decision**: Status transitions are enforced server-side. A task can only move to `in_progress` if all dependencies have status `done`. A task can only move to `done` if it is `in_progress`. The frontend shows locked tasks as grayed + lock icon.
- **Why**: Server-side enforcement prevents invalid states. The visual lock gives game-like feedback.

## Risks / Trade-offs

- **Risk**: AI may generate poor dependency graphs (too linear, missing parallelism, cycles).
  - Mitigation: Validate DAG structure post-generation (topological sort check). Add prompt engineering to encourage parallel paths. Add cycle detection with fallback to linear ordering.
- **Risk**: Dropping existing boards frustrates users with existing data.
  - Mitigation: This is an early-stage product (MVP). Warn users and provide a "regenerate" path.
- **Risk**: React Flow + dagre adds ~150KB to the frontend bundle.
  - Mitigation: Lazy-load the DAG view component. React Flow supports tree-shaking.
- **Risk**: No manual dependency editing means users are stuck with AI decisions.
  - Mitigation: Acknowledged as a known limitation for MVP. Future proposal will add manual editing.

## Migration Plan

1. Create new Alembic migration:
   - Drop `subtask`, `task`, `board_column`, `board` tables (cascade)
   - Recreate `board` table (same schema minus column references)
   - Create `task` table with `board_id` FK (instead of `column_id`), add `status` field
   - Create `task_dependency` junction table
   - Recreate `subtask` table with same schema
2. Frontend: replace all board components with DAG view
3. Regenerate Orval API client after backend schema changes
4. Rollback: revert migration (recreates old tables, but data is lost)

## Open Questions

- None remaining after user Q&A session. All key decisions have been made.
