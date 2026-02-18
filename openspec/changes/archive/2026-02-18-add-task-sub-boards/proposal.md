# Change: Add Task Sub-Boards (Nested DAG for Complex Tasks)

## Why

Users need a way to break down complex tasks into their own structured plans. Currently, tasks can only have flat subtask checklists, which is insufficient for multi-step, dependency-rich work. By allowing any task to be expanded into a sub-board (a full DAG), users get deeper planning without leaving the familiar board experience. This bridges the gap between simple checklist items and full goal-level boards.

## What Changes

- **Board model**: Add optional `parent_task_id` FK to Board, making `goal_id` nullable. Sub-boards are boards linked to a parent task instead of a goal.
- **Task model**: Add computed `has_sub_board` indicator. When a task has a sub-board, its subtasks are removed/hidden (sub-board replaces subtasks).
- **Sub-board generation API**: New `POST /api/tasks/:id/generate-sub-board` SSE endpoint. Uses a lighter AI flow: derives context from parent task, asks 2-4 focused questions, then generates a smaller DAG (3-15 tasks).
- **Sub-board question flow**: New `POST /api/tasks/:id/sub-board-questions` endpoint that generates focused questions about how to break down the task. Answers are submitted, then sub-board is generated.
- **Completion propagation**: When a sub-board's goal node is marked done, the parent task auto-transitions to `done`.
- **Auto-start**: When a sub-board is created for a task, the parent task auto-transitions to `in_progress` (if dependencies are met).
- **Board list filtering**: `GET /api/boards` returns only top-level boards (where `parent_task_id IS NULL`). Sub-boards are accessed through their parent task.
- **Frontend: Task node visual treatment**: Tasks with sub-boards get a distinct icon (layers/graph) and border accent (dashed or colored) to clearly indicate they contain a board.
- **Frontend: Breadcrumb navigation**: A breadcrumb bar replaces the hardcoded back button on the board page, showing the path from Home through parent boards to the current board.
- **Frontend: Sub-board creation inline flow**: Questions and generation happen inside the task detail panel, no page navigation needed.
- **Nesting limit**: Sub-boards are limited to 1 level deep. Tasks on sub-boards cannot themselves have sub-boards.
- **No dissolve**: Once a sub-board is created, it cannot be converted back to subtasks (out of scope for this change).

## Impact

- Affected specs: `board-management`, `board-ui`, `ai-pipeline`, `task-dag`
- Affected backend code:
  - `app/domains/boards/models.py` — Board model (add `parent_task_id`), Task model (add relationship)
  - `app/domains/boards/schemas.py` — BoardResponse, TaskResponse, new sub-board schemas
  - `app/domains/boards/board_service.py` — Sub-board creation, board list filtering
  - `app/domains/boards/board_repository.py` — Queries for sub-boards, parent chain
  - `app/domains/boards/task_service.py` — Completion propagation, auto-start logic
  - `app/domains/boards/router.py` — New endpoints for sub-board questions and generation
  - `app/domains/boards/dag_utils.py` — Nesting depth validation
  - `app/domains/ai/nodes/generate_board.py` — Sub-board skeleton generation variant
  - `app/domains/ai/prompts/generate_board.py` — Sub-board skeleton prompt
  - `app/domains/ai/prompts/sub_board_questions.py` — New prompt for sub-board questions
  - `app/domains/ai/service.py` — New service functions for sub-board question generation and sub-board generation
  - `migrations/` — New Alembic migration for Board.parent_task_id
- Affected frontend code:
  - `frontend/src/features/board/components/task-node.tsx` — Sub-board visual indicator
  - `frontend/src/features/board/components/dag-view.tsx` — Breadcrumb integration
  - `frontend/src/features/board/components/task-detail-panel.tsx` — Sub-board creation flow, navigation to sub-board
  - `frontend/src/features/board/components/breadcrumb-nav.tsx` — New component
  - `frontend/src/routes/boards.$boardId.tsx` — Breadcrumb bar, context-aware back button
  - `frontend/src/routes/index.tsx` — Filter to top-level boards only (already handled by backend)
  - `frontend/src/features/board/utils/dagre-layout.ts` — Sub-board task node styling
