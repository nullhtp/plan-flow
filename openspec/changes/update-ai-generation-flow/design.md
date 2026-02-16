## Context

The current board generation is a single monolithic LLM call that produces the entire board at once — task names, descriptions, metadata, and dependency graph. The user waits 15-30 seconds with no feedback. The single-call approach also limits output quality because the LLM must balance structure design with content generation in one pass.

Additionally, the system always responds in English regardless of the user's input language.

This change splits the generation into two steps, streams partial results to the client via SSE, adds language detection to the classification node, and auto-generates subtasks for all tasks during board generation.

## Goals / Non-Goals

- **Goals:**
  - Detect user's input language during classification and generate all AI outputs in that language
  - Split board generation into skeleton (structure) and enrichment (content) steps
  - Run task enrichment calls in parallel with configurable concurrency
  - Stream generation progress to the client via SSE events
  - Auto-generate subtasks for every task during the enrichment step
  - Maintain DAG validation guarantees (no cycles, single goal node)

- **Non-Goals:**
  - Frontend SSE consumption (separate change)
  - Translation of existing boards or UI labels
  - Per-step model selection (same model for all steps)
  - Changing the classification or question generation flows (only adding language detection to classification output)

## Decisions

### Decision 1: Two-step generation graph (skeleton → parallel enrichment)

**What:** Replace the single `generate_board` node with two stages:
1. **Skeleton node** — generates task names, the full dependency graph (`depends_on` edges), `is_goal_node` flags, and `board_title`. No descriptions, no metadata, no subtasks.
2. **Enrichment node** — called once per task in parallel. Receives the task's name, its position in the graph (dependencies, dependents), the goal context, and the detected language. Produces: `description`, `due_date`, `priority`, `estimated_minutes`, and `subtasks` (list of subtask titles).

**Why:** Separating structure from content lets the LLM focus on one concern at a time. The skeleton is a smaller output that completes faster, giving the user immediate visual feedback. Enrichment calls are independent per task and can run concurrently.

**Alternatives considered:**
- Three steps (skeleton → descriptions → subtasks): Over-fragmented; the enrichment per task is small enough to combine description + metadata + subtasks in one call.
- Single call with streaming token output: LangChain structured output doesn't support partial parsing of complex nested schemas reliably.

### Decision 2: SSE streaming via FastAPI `StreamingResponse`

**What:** The `POST /api/goals/:id/generate-board` endpoint returns `text/event-stream` instead of JSON. Events:

| Event | Data | When |
|-------|------|------|
| `skeleton_ready` | `{board_id, title, tasks: [{id, title, depends_on, is_goal_node}], edges: [{source, target}]}` | Skeleton generated + Board/Task records persisted (without descriptions) |
| `task_enriched` | `{task_id, description, due_date, priority, estimated_minutes, subtasks: [{id, title}]}` | One task's enrichment completes and is persisted |
| `generation_complete` | `{board_id}` | All tasks enriched, goal status → active |
| `generation_error` | `{error, message, detail?}` | Any unrecoverable error during generation |

**Why:** SSE is simpler than WebSockets for a server-push-only scenario. FastAPI supports `StreamingResponse` natively. The client can render the board skeleton immediately and progressively fill in task details.

**Implementation:** Use an `async def generate()` generator function that yields SSE-formatted strings. The generator orchestrates the skeleton call, persists the skeleton, yields `skeleton_ready`, then runs enrichment calls via `asyncio.Semaphore`-bounded `asyncio.gather`, yielding `task_enriched` for each completed task, and finally yields `generation_complete`.

### Decision 3: Language detection piggybacked on classification

**What:** Extend `ClassificationOutput` with a `language` field (ISO 639-1 code, e.g., "en", "ru", "es"). The classification prompt is updated to also detect the input language. The detected language is stored in `goal.ai_context` alongside the classification and passed to all downstream nodes.

**Why:** The classification LLM call already reads the full goal text — detecting language is trivial additional work with no extra API cost. A separate detection step would add latency and cost for minimal benefit.

### Decision 4: Configurable concurrency for parallel enrichment

**What:** Add a `ai_enrichment_concurrency` setting (default: 5) to `core/config.py`. The enrichment step uses an `asyncio.Semaphore(settings.ai_enrichment_concurrency)` to limit concurrent LLM calls.

**Why:** Firing 15-20 concurrent LLM calls may hit OpenRouter rate limits or cause throttling. A semaphore provides back-pressure without complex batching logic. The default of 5 balances speed and API friendliness.

### Decision 5: Skeleton persistence before enrichment

**What:** After the skeleton step, persist the Board and Task records immediately (with empty descriptions and no subtasks). Then enrich tasks and update records individually as enrichment completes.

**Why:** This lets us send `skeleton_ready` with real database IDs (UUIDs) so the frontend can render the board graph immediately. If enrichment fails partway, we have a partial board that can be retried or completed manually. The goal status transitions to `active` only after all enrichment completes.

**Trade-off:** If enrichment fails for some tasks, we have a board with incomplete task details. We add a `generating` status check — if the goal is still in `generating` status when the board is fetched, the frontend can show a loading state for un-enriched tasks.

### Decision 6: Enrichment retry scope

**What:** Each individual task enrichment has its own retry loop (up to `ai_max_retries` attempts). If a single task's enrichment fails after all retries, the system sends a `generation_error` event for that task but continues enriching other tasks. After all enrichment attempts, if any tasks failed, the system still sends `generation_complete` but includes a `failed_tasks` list. The goal still transitions to `active` — tasks with failed enrichment will have empty descriptions and no subtasks.

**Why:** One bad task shouldn't block the entire board. The user can manually edit tasks that the AI couldn't enrich, or trigger re-enrichment later.

### Decision 7: Subtask schema in enrichment output

**What:** The enrichment output Pydantic model includes a `subtasks` field: `list[SubtaskOutput]` where `SubtaskOutput` has `title: str`. Subtasks are persisted as `Subtask` records with fractional index positions assigned in order.

**Why:** Subtasks are lightweight (just titles + completion state). Generating them alongside the description in the enrichment call adds minimal overhead and produces better subtasks because the LLM has the full task description context.

## Risks / Trade-offs

- **Increased total LLM cost**: Two-step generation makes N+1 LLM calls (1 skeleton + N task enrichments) instead of 1. However, each call is smaller, and the enrichment calls use less tokens per call. Net cost increase is estimated at 20-40%.
  → Mitigation: Configurable concurrency limits API pressure. Future optimization: per-step model selection (cheaper model for enrichment).

- **Partial board on enrichment failure**: If some enrichment calls fail, the board has tasks with empty descriptions.
  → Mitigation: Frontend shows placeholder state for un-enriched tasks. Manual editing always available.

- **SSE connection dropped mid-generation**: If the client disconnects, the server continues generating in the background.
  → Mitigation: The board is being persisted progressively, so the client can fetch the board state via GET on reconnect. No data is lost.

- **Skeleton retry changes**: The skeleton must produce a valid DAG. If it fails validation, the entire skeleton is retried (same as current behavior). Enrichment retries are per-task.

## Migration Plan

1. This is a **breaking change** to the `POST /goals/:id/generate-board` endpoint — it changes from JSON response to SSE stream.
2. No database migration needed — existing models (Board, Task, Subtask, TaskDependency) are reused as-is.
3. Frontend must be updated to consume SSE (separate change).
4. During transition, both old JSON and new SSE behavior could coexist via Accept header negotiation, but this adds complexity. Since it's a solo project with no external consumers, a clean switch is preferred.

## Open Questions

- None — all questions resolved during proposal discussion.
