## Context

PlanFlow currently supports a flat DAG structure: each Goal produces one Board with tasks connected by dependencies. Tasks can have subtask checklists, but these are simple checkboxes with no dependency structure. For complex tasks (e.g., "Find and secure housing in Lisbon" within a relocation goal), a flat checklist is insufficient — the user needs a full DAG with parallel paths, dependencies, and convergence nodes.

This change introduces sub-boards: any task on a root board can be expanded into its own full DAG board. The sub-board uses the same visualization, generation, and interaction patterns as root boards, but is linked to a parent task instead of a goal.

### Stakeholders
- End users: need deeper task breakdown for complex work
- AI pipeline: needs a new entry point for sub-board generation with lighter context
- Frontend: needs navigation between board levels and visual differentiation

## Goals / Non-Goals

### Goals
- Allow any task on a root-level board to be expanded into a sub-board (full DAG)
- Use a lighter AI question flow (2-4 questions derived from parent task context)
- Sub-board visually distinct from regular tasks on the parent board
- Easy navigation between root and sub-board via breadcrumbs
- Auto-complete parent task when sub-board's goal node is done
- Sub-board generation happens inline in the task detail panel (no page navigation)

### Non-Goals
- Multi-level nesting (sub-boards of sub-boards) — limited to 1 level deep
- Dissolving a sub-board back into subtasks
- Manual sub-board creation (without AI) — always AI-generated
- Collaborative sub-boards (still single-user, as per MVP constraints)
- Showing sub-boards on the home page board list

## Decisions

### 1. Board model: `parent_task_id` nullable FK instead of separate SubBoard model

**Decision**: Add an optional `parent_task_id` FK to the existing Board model. Make `goal_id` nullable (sub-boards inherit the root board's goal).

**Rationale**: A sub-board IS a board — it has the same tasks, edges, goal node, and layout. Using the same model avoids duplicating all board-related queries, services, and UI components. The `parent_task_id` field distinguishes sub-boards from root boards.

**Alternatives considered**:
- Separate `SubBoard` model: rejected — would require duplicating board CRUD, task CRUD, all board-level AI features, and React Flow rendering.
- Storing sub-board as a JSON blob on the task: rejected — loses all relational query capabilities and API consistency.

### 2. Sub-board replaces subtasks on the parent task

**Decision**: When a sub-board is created for a task, existing subtasks are deleted. The sub-board's tasks replace the subtask checklist entirely. The task detail panel shows a "Sub-Board" section with a summary + "Open" button instead of the subtask checklist.

**Rationale**: Having both subtasks (flat checklist) and a sub-board (full DAG) on the same task creates confusion about which level of detail represents the actual work breakdown. The sub-board is strictly more capable than subtasks.

### 3. Lighter AI question flow for sub-boards

**Decision**: A new `POST /api/tasks/:id/sub-board-questions` endpoint generates 2-4 focused questions using the parent task's title, description, board title, and goal context. No classification step — the task is already classified as part of the parent board. No follow-up rounds. Answers are submitted via `POST /api/tasks/:id/sub-board-answers`, then generation is triggered.

**Rationale**: The parent task already has rich context from the original goal classification and board generation. The questions only need to fill in specifics about how the user wants to decompose this particular task.

**Alternatives considered**:
- Full goal creation flow: rejected — too heavy, redundant classification, unnecessary for a task that's already part of a plan.
- Zero questions (fully automatic): rejected — user wants some input on how the breakdown should look (same reason the main flow has questions).

### 4. Sub-board skeleton prompt: smaller scope

**Decision**: The sub-board skeleton prompt generates 3-15 tasks (vs. 5-30 for root boards). It receives the parent task's title, description, the root board's title and goal context, and the user's answers to the sub-board questions. It still produces a valid DAG with a single goal node.

**Rationale**: Sub-boards are inherently smaller scope — they decompose a single task, not an entire goal.

### 5. Completion propagation: goal node done -> parent task done

**Decision**: When the sub-board's goal node transitions to `done`, the system automatically transitions the parent task to `done`. If the parent task is `not_started` and dependencies are met, it first transitions to `in_progress` then to `done`. This is enforced server-side in the task status transition logic.

**Rationale**: The sub-board's goal node represents the completion of the parent task's work. Manual completion after the sub-board is done would be redundant friction.

### 6. Auto-start parent task on sub-board creation

**Decision**: When a sub-board is successfully generated for a task, the parent task auto-transitions to `in_progress` (if its dependencies are met and it's currently `not_started`).

**Rationale**: Creating a sub-board is an act of starting work on the task. Leaving it as `not_started` would be inconsistent.

### 7. Nesting depth: 1 level only

**Decision**: Tasks on sub-boards cannot themselves have sub-boards. The "Expand to Board" action is only available for tasks on root-level boards. Enforced both in the API (reject sub-board creation for tasks whose board has a `parent_task_id`) and in the UI (don't show the expand button on sub-board tasks).

**Rationale**: Multi-level nesting introduces complex navigation, deep breadcrumbs, and cascading completion chains. 1 level covers the 90% use case. Can be extended later if needed.

### 8. Frontend navigation: breadcrumbs + same URL structure

**Decision**: Sub-boards use the same `/boards/:boardId` URL. A breadcrumb bar at the top shows the navigation chain: `Home / Board Title / Parent Task Title`. Clicking "Home" goes to `/`, clicking "Board Title" goes to the parent board, clicking the current segment is a no-op. The old hardcoded back button is replaced by this breadcrumb.

**Rationale**: Using the same URL structure means all existing board features (task detail panel, chat, status toggling, etc.) work unchanged for sub-boards. The breadcrumb provides context and navigation.

**Implementation**: The backend includes `parent_task_id` and `parent_board_id` (nullable, computed) in the BoardResponse. When non-null, the frontend renders the breadcrumb chain. For 1-level nesting, the chain is at most 3 segments.

### 9. Visual treatment for sub-board tasks on the parent board

**Decision**: A task node that has a sub-board gets:
- A small "layers" icon (or similar graph icon) in the top-right corner of the node
- A dashed border instead of solid
- A progress summary replacing the subtask count (e.g., "3/8 tasks" from the sub-board)

**Rationale**: The dashed border + icon makes these tasks visually distinct without being heavy. The progress summary gives at-a-glance status of the sub-board without opening it.

### 10. Home page board list: top-level only

**Decision**: `GET /api/boards` filters to `parent_task_id IS NULL` by default. Sub-boards don't appear on the home page.

**Rationale**: Sub-boards are contextual to their parent task. Showing them on the home page would create a confusing flat list mixing different nesting levels.

## Risks / Trade-offs

- **Board-Goal coupling relaxed**: Making `goal_id` nullable on Board breaks the current 1:1 assumption. Mitigated by: sub-boards still belong to a root board that has a goal; any code that accesses `board.goal_id` must handle the nullable case.
- **Completion propagation complexity**: Auto-completing the parent task when the sub-board is done could surprise users. Mitigated by: clear visual feedback (parent task transitions with animation), and the user explicitly marked the sub-board's goal node as done.
- **Subtask deletion on sub-board creation**: Removing existing subtasks is destructive. Mitigated by: confirmation dialog warns the user before creating a sub-board if subtasks exist.
- **Board generation cost**: Each sub-board generation costs LLM API calls (questions + skeleton + enrichment). Mitigated by: smaller skeleton (3-15 tasks), same concurrency limits.

## Migration Plan

1. **Alembic migration**: Add `parent_task_id` (nullable FK to task) to `board` table. Make `goal_id` nullable. Add index on `parent_task_id`.
2. **Backward compatibility**: All existing boards have `parent_task_id = NULL` and `goal_id` set. No data migration needed.
3. **API backward compatibility**: `GET /api/boards` returns only root boards (same as before since no sub-boards exist yet). `GET /api/boards/:id` works for both root and sub-boards.
4. **Frontend**: Breadcrumb gracefully handles root boards (shows just "Home / Board Title" — same as current back button but richer).

## Open Questions

- None — all key decisions resolved through user Q&A.
