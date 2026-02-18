## MODIFIED Requirements

### Requirement: Board Generation Node
The system SHALL implement a two-step board generation pipeline replacing the single-call board generation node. **Step 1 (Skeleton):** A LangGraph node SHALL generate the board structure from goal context. The skeleton node SHALL receive: the goal's original text, classification output (domain, complexity, dimensions, language), all Q&A pairs, and the formatted `user_meta` context (when available). The skeleton output SHALL conform to a Pydantic schema (`BoardSkeletonOutput`) containing: `board_title` (string), and `tasks` (array of objects each with `id` (string, e.g., "t1"), `title`, `depends_on` (array of task id strings), and `is_goal_node` (boolean, default false)). The output MUST form a valid DAG — no circular dependencies. Tasks with an empty `depends_on` array are root tasks. Exactly one task MUST have `is_goal_node: true`. All generated content (board_title, task titles) SHALL be in the language detected during classification. **Step 2 (Enrichment):** For each task produced by the skeleton, a separate LLM call SHALL generate: `description` (string), `due_date` (nullable ISO date string), `priority` (nullable, one of "low"/"medium"/"high"), `estimated_minutes` (nullable integer), and `subtasks` (array of objects each with `title` (string)). The enrichment output SHALL conform to a Pydantic schema (`TaskEnrichmentOutput`). Enrichment calls SHALL run in parallel with concurrency bounded by a configurable limit (`ai_enrichment_concurrency`, default 5) using `asyncio.Semaphore`. Each enrichment call receives the task title, its dependency and dependent task titles (for context), the full goal context, the detected language, and the formatted `user_meta` context (when available). All generated content SHALL be in the detected language. The enrichment prompts SHALL be stored as a separate module in `prompts/enrich_task.py`. The skeleton prompt SHALL be stored in `prompts/generate_board.py` (updated). **Step 3 (Subtask Action Generation):** After each task's enrichment is persisted (subtask records exist in the database), a follow-up LLM call SHALL generate actions for the task's subtasks using `generate_subtask_actions`. This call receives the task title, description, status, and the list of subtask titles. The LLM returns action data (label, icon, prompt) for subtasks that can be meaningfully automated, and null for non-automatable subtasks. The generated actions SHALL be persisted on the Subtask records. Action generation failure SHALL NOT block or fail the enrichment — subtasks are created without actions on failure (graceful degradation). Action generation calls SHALL reuse the same concurrency semaphore as enrichment.

#### Scenario: Skeleton generated for a relocation goal with dependencies
- **WHEN** the skeleton node receives a relocation goal with classification domain "relocation", complexity 4, and answers covering timeline, budget, housing, and logistics
- **THEN** the output contains 10-20 tasks with dependency edges forming a DAG, task titles only (no descriptions), root tasks with empty `depends_on`, and exactly one task with `is_goal_node: true`

#### Scenario: Parallel paths in skeleton
- **WHEN** the skeleton node produces output for a goal with multiple independent dimensions
- **THEN** the output contains parallel task chains that converge at shared milestone tasks before ultimately feeding into the final goal node

#### Scenario: Final goal node is the single sink of the DAG
- **WHEN** the skeleton node produces output
- **THEN** exactly one task has `is_goal_node: true`, it has no dependents (nothing depends on it), and all other leaf tasks are dependencies of the goal node

#### Scenario: Skeleton task count within bounds
- **WHEN** the skeleton node produces output
- **THEN** the total task count is between 5 and 30

#### Scenario: No circular dependencies in skeleton output
- **WHEN** the skeleton node produces output
- **THEN** performing a topological sort on the task dependency graph succeeds (no cycles detected)

#### Scenario: Skeleton uses user meta for realistic planning
- **WHEN** the skeleton node receives a goal with `user_meta` containing `current_datetime: "2026-02-17T14:30:00Z"` and `timezone: "Europe/Berlin"`
- **THEN** the AI MAY use the current date and timezone to inform task sequencing and timeline-aware planning

#### Scenario: Task enriched with description and metadata
- **WHEN** the enrichment node is called for a task "Research neighborhoods in Lisbon"
- **THEN** the output includes a description (e.g., "Research the best neighborhoods..."), progressive metadata (due_date, priority, estimated_minutes) where relevant, and 2-5 subtasks with titles

#### Scenario: Enrichment uses current date for due dates
- **WHEN** the enrichment node is called for a task with `user_meta.current_datetime = "2026-02-17T14:30:00Z"`
- **THEN** the AI MAY set `due_date` relative to the current date (e.g., "2026-03-01" for a task due in 2 weeks)

#### Scenario: Subtasks generated during enrichment
- **WHEN** the enrichment node enriches a task
- **THEN** the output includes 2-5 subtasks with actionable titles relevant to the parent task

#### Scenario: Enrichment in detected language
- **WHEN** the enrichment node is called for a task whose goal was classified with language "ru"
- **THEN** the description, subtask titles, and all textual content are in Russian

#### Scenario: Parallel enrichment with concurrency limit
- **WHEN** enrichment runs for 15 tasks with `ai_enrichment_concurrency` set to 5
- **THEN** at most 5 enrichment LLM calls execute concurrently

#### Scenario: Single task enrichment failure does not block others
- **WHEN** enrichment for task "t3" fails after all retries but enrichment for other tasks succeeds
- **THEN** other tasks are fully enriched and task "t3" has empty description and no subtasks

#### Scenario: Subtask actions generated after enrichment persistence
- **WHEN** enrichment for a task is persisted and subtask records exist
- **THEN** a follow-up LLM call generates actions for automatable subtasks and persists action_label, action_icon, action_prompt on the Subtask records

#### Scenario: Subtask action generation failure does not block enrichment
- **WHEN** subtask action generation fails for a task after retries
- **THEN** the subtasks exist without actions (action fields remain null) and the enrichment is still considered successful

#### Scenario: Mixed automatable and non-automatable subtasks
- **WHEN** action generation runs for subtasks ["Draft agreement", "Visit notary", "Research options"]
- **THEN** "Draft agreement" and "Research options" get actions; "Visit notary" gets null action fields

## ADDED Requirements

### Requirement: Subtask Action Generation AI Service Function
The system SHALL provide an async function `generate_subtask_actions(task_title: str, task_description: str, task_status: str, subtasks: list[dict], model: str | None = None) -> list[SubtaskActionOutput]` in the AI service layer. The function SHALL call the LLM with structured output using the subtask action prompt and the task/subtask context. The function SHALL use `AI_ACTION_SUGGEST_MODEL` (falling back to `AI_CHAT_MODEL`, then `AI_DEFAULT_MODEL`). The function SHALL return one `SubtaskActionOutput` per input subtask, with null action fields for non-automatable subtasks. The function SHALL NOT use LangGraph or tools — it is a single structured output LLM call.

#### Scenario: Service function called with task context
- **WHEN** `generate_subtask_actions` is called with task title "Create rental agreement" and subtasks ["Draft agreement terms", "Get notary appointment"]
- **THEN** it returns a list with action data for "Draft agreement terms" and null actions for "Get notary appointment"

#### Scenario: Language matching in service function
- **WHEN** `generate_subtask_actions` is called with German task title and subtask titles
- **THEN** returned action labels and prompts are in German

### Requirement: Subtask Action Prompt Module
The system SHALL store the subtask action system prompt in `app/domains/ai/prompts/action_suggestions.py` (repurposed). The prompt SHALL instruct the LLM to: analyze each subtask in the context of the parent task title, description, and status; determine if AI can meaningfully help with each subtask; generate an action (label, icon, prompt) only for automatable subtasks; return null action fields for subtasks requiring physical presence, manual work, or human interaction; use the same language as the task content; vary action types (icons) across subtasks; write the `prompt` field as a natural instruction that references the specific subtask. The prompt SHALL receive the task title, description, status, and a list of subtask titles.

#### Scenario: Prompt stored as module
- **WHEN** the subtask action generation feature is invoked
- **THEN** the system prompt is loaded from `app/domains/ai/prompts/action_suggestions.py`
