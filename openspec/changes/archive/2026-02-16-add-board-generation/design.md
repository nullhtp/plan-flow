## Context

This is M3 — the second AI-powered milestone. M2 (Goal Understanding) established the AI pipeline with classification and question generation. This change adds the board generation node that takes the accumulated context (goal + classification + Q&A) and produces a complete kanban board with custom columns and tasks.

The `boards` domain is entirely new. The `ai` domain's pipeline and service layer need extension. The `goals` domain needs new status transitions.

Solo developer, full-time. M2 infrastructure (LangGraph, OpenRouter, structured output) is already in place.

## Goals / Non-Goals

### Goals
- AI generates a complete board with goal-specific columns (not generic To Do/Doing/Done)
- Each column has a title, description, and position reflecting the goal's natural workflow phases
- Tasks are actionable, concrete, and logically distributed across columns
- Progressive metadata (due date, priority, time estimate) applied per-task only when relevant
- Board, Column, and Task data persisted in normalized tables with proper relationships
- API endpoints for triggering generation and retrieving the board
- Frontend "Generate Board" button enabled on the goal summary page

### Non-Goals
- Board view UI (kanban layout, task cards) — separate proposal
- Drag-and-drop reordering — separate proposal
- Manual task/column CRUD — separate proposal
- Subtask generation — can be added later
- Board re-generation or adaptation — M6
- Streaming/SSE for board generation — add later if latency is a problem

## Decisions

### Board Generation as Explicit User Action

**Decision:** Board generation is triggered by the user clicking "Generate Board" on the goal summary page, which calls `POST /api/goals/:id/generate-board`. It does not happen automatically when the goal reaches `answered` status.

**Why:** Gives the user agency. They can review the Q&A summary before committing to generation. Also avoids wasted LLM calls if the user wants to edit answers first. Consistent with the M2 pattern where the user explicitly submits answers.

### Synchronous Response

**Decision:** `POST /api/goals/:id/generate-board` runs the AI generation synchronously and returns the full board in the response. Same pattern as M2's goal creation endpoint.

**Why:** Board generation should complete in 3-8 seconds with a capable model. This is within acceptable HTTP response time. Async polling adds significant complexity. If latency becomes a problem, we can add SSE later (same upgrade path as M2).

**Timeout:** Route timeout 45 seconds. LLM call timeout remains 20 seconds (board generation is a single LLM call with a larger output).

### AI Output Schema: Flat Columns with Nested Tasks

**Decision:** The AI outputs a single JSON object containing an array of columns, each with a nested array of tasks. The Pydantic schema:

```python
class BoardGenerationTaskOutput(BaseModel):
    title: str
    description: str
    position: int
    due_date: str | None  # ISO date or null
    priority: str | None  # "low", "medium", "high", or null
    estimated_minutes: int | None  # or null

class BoardGenerationColumnOutput(BaseModel):
    title: str
    description: str
    position: int
    tasks: list[BoardGenerationTaskOutput]

class BoardGenerationOutput(BaseModel):
    board_title: str
    columns: list[BoardGenerationColumnOutput]
```

**Why:** Mirrors the database structure. The AI assigns positions explicitly. Progressive metadata fields are nullable — the AI populates them only when relevant to the specific task and goal type.

### Column Count Tied to Complexity

**Decision:** The board generation prompt instructs the AI to produce 3-7 columns, using the classification's `complexity` score as a guide: simpler goals (1-2) get 3-4 columns, complex goals (4-5) get 5-7 columns. The AI decides the exact count.

**Why:** Prevents both trivially thin and overwhelmingly wide boards. The complexity score from classification is already a good proxy for how many workflow phases a goal needs.

### Task Count Bounds

**Decision:** The prompt instructs the AI to produce 2-6 tasks per column, with a soft cap of 30 total tasks per board. The AI distributes tasks logically across columns.

**Why:** Keeps boards actionable. Too few tasks and the board isn't useful. Too many and it's overwhelming. 30 tasks across 5 columns is ~6 per column, which is manageable on a kanban view.

### Progressive Metadata: Per-Task Decision

**Decision:** The AI decides independently for each task which metadata fields to include. A "Research visa requirements" task might get `priority: "high"` and `estimated_minutes: 60` but no `due_date`. A "Book flight" task might get all three. A "Brainstorm ideas" task might get none.

**Why:** Different tasks within the same goal have different needs. Per-task granularity produces more useful metadata than a blanket per-board decision. The nullable fields in the schema naturally support this.

### Database: Normalized Board/Column/Task Tables

**Decision:** Three new tables:
- `board` — id, goal_id (FK, unique), title, created_at, updated_at
- `column` — id, board_id (FK), title, description, position, created_at, updated_at
- `task` — id, column_id (FK), title, description, position, due_date, priority, estimated_minutes, created_at, updated_at

Board has a one-to-one relationship with Goal (one board per goal). Column position and task position are integers for ordering.

**Why:** Normalized tables enable future CRUD operations (move tasks, add columns, edit tasks) without JSON manipulation. The `goal_id` unique constraint on board enforces one board per goal. Position integers are simple and well-understood for ordering.

**Alternatives considered:**
- Store board as JSON in `goal.ai_context` — simpler but blocks future task-level operations (status changes, comments, drag-and-drop persistence).
- Include a Subtask table — deferred. Can be added later without breaking the board/column/task structure.

### Board-Goal Relationship

**Decision:** One-to-one: each goal produces exactly one board. The `board` table has a unique constraint on `goal_id`. Re-generating a board (future M6 feature) would replace the existing board.

**Why:** MVP simplicity. A goal is a single plan. If we ever need board versioning, we can add a `version` field or an archive table later.

### Pipeline Extension Strategy

**Decision:** Add `generate_board` as a new LangGraph node in the existing pipeline. However, board generation is invoked separately from the classify+questions flow — it's a distinct entry point in the AI service (`generate_board(goal)`) that runs only the board generation node, not the full pipeline.

**Why:** Board generation needs different input (full goal context including answers) and is triggered at a different time (after answers, not during goal creation). Making it a separate entry point keeps the pipeline simple while reusing the same infrastructure (LangGraph, structured output, retry logic).

### Prompt Strategy

**Decision:** The board generation prompt receives: goal text, classification (domain, complexity, dimensions), all Q&A pairs (initial + follow-up). It instructs the AI to:
1. Design columns as workflow phases specific to the goal domain
2. Name columns with action-oriented or phase-oriented titles
3. Create concrete, actionable tasks distributed logically across columns
4. Assign progressive metadata only when it adds planning value
5. Order columns from earliest/first phase to latest/final phase
6. Order tasks within columns by suggested execution order

**Why:** The prompt must be explicit about what makes a good board vs. a generic one. The classification dimensions and Q&A answers provide the specificity needed for custom column names and relevant tasks.

## Risks / Trade-offs

- **LLM output quality** — board quality depends heavily on the prompt. A bad prompt produces generic "To Do/Doing/Done" columns or vague tasks. Mitigation: detailed prompt with examples, structured output enforcement, testing with diverse goal types.
- **LLM latency** — board generation produces more output tokens than classification or questions. May take 5-10 seconds. Mitigation: loading UI, 45-second route timeout, can add streaming later.
- **Token cost** — board generation prompts are larger (include full Q&A context) and produce more output. Mitigation: monitor cost per generation, consider cheaper models for simpler goals.
- **Position gaps** — if tasks are later deleted or moved, position integers may have gaps. Mitigation: positions are relative ordering, gaps don't break sorting. Can normalize positions on read if needed.

## Open Questions

- Exact route timeout for board generation (proposed 45s — may need tuning)
- Whether to include a `board_id` FK on the Goal model or only navigate via `Board.goal_id` (proposed: only `Board.goal_id` with a unique constraint, query board by goal_id when needed)
