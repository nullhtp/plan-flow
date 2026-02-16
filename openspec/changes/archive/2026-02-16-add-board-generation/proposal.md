# Change: Add Board Generation Pipeline (M3)

## Why

After M2 (Goal Understanding), the user has a goal, classification data, and answered questions — but no actionable plan. Board generation is the payoff: turning all that context into a structured kanban board with goal-specific columns and concrete tasks. Without this, the product stops at "we understood your goal" and never delivers a plan.

This is **M3** on the roadmap — the milestone that produces the first tangible output users can act on.

## What Changes

### Backend — New `boards` Domain
- Board, Column, and Task SQLModels with proper relationships and position tracking
- `POST /api/goals/:id/generate-board` — triggers AI board generation for an `answered` goal, persists the result, returns the full board
- `GET /api/boards/:id` — retrieves a board with its columns and tasks (nested response)
- Alembic migration for `board`, `column`, and `task` tables

### Backend — AI Pipeline Extension
- **Board generation node** — new LangGraph node that takes goal text + classification + all Q&A as input and produces a structured board with custom columns and tasks
- **Board generation Pydantic schemas** — output schema for the AI: columns (title, description, position) with nested tasks (title, description, position, progressive metadata)
- **Board generation system prompt** — stored in `prompts/generate_board.py`, instructs the AI to create goal-specific workflow columns (not generic "To Do/Doing/Done"), actionable tasks, logical ordering, and per-task progressive metadata (due date, priority, time estimate — only when relevant)
- **Pipeline state extension** — add board generation output to `GoalPipelineState`
- **AI service function** — `generate_board(goal_id)` exposed to callers

### Backend — Goal Status Transitions
- Enable `answered` -> `generating` -> `active` status transitions on the Goal model
- `POST /goals/:id/generate-board` transitions goal through `generating` -> `active`

### Frontend — Goal Summary Update
- Enable the "Generate Board" button on the post-answer summary page
- Add loading state during board generation
- Redirect to board view route after successful generation (board view itself is out of scope — will be a separate proposal)

## Impact
- Affected specs: `ai-pipeline` (new node, extended pipeline), `goal-management` (new status transitions, board FK)
- New specs: `board-management` (new capability)
- Affected code:
  - New: `backend/app/domains/boards/` (models, schemas, router, service)
  - New: `backend/app/domains/ai/nodes/generate_board.py`
  - New: `backend/app/domains/ai/prompts/generate_board.py`
  - Modified: `backend/app/domains/ai/schemas.py` (board output schema)
  - Modified: `backend/app/domains/ai/pipeline.py` (add generate_board node)
  - Modified: `backend/app/domains/ai/service.py` (add generate_board function)
  - Modified: `backend/app/domains/goals/service.py` (status transitions for board generation)
  - Modified: `backend/app/main.py` (register boards router)
  - Modified: `frontend/src/features/goals/components/goal-summary.tsx` (enable Generate Board button)
  - New: Alembic migration for board, column, task tables
