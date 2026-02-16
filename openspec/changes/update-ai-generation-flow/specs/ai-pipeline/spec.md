## MODIFIED Requirements

### Requirement: Goal Classification Node
The system SHALL implement a LangGraph node that classifies a goal from raw text input. The classification output SHALL conform to a Pydantic schema containing: `domain` (string — e.g., "relocation", "learning", "product-launch"), `complexity` (integer 1-5), `confidence` (float 0.0-1.0), `dimensions` (list of strings — key aspects to explore), `suggested_title` (a clean, concise title derived from the raw input), and `language` (string — ISO 639-1 language code detected from the input, e.g., "en", "ru", "es", "de"). The classification prompt SHALL be stored as a separate module in `prompts/classify.py`. The detected language SHALL be stored in the goal's `ai_context` and passed to all downstream pipeline nodes so that all AI-generated content is produced in the user's input language.

#### Scenario: Clear goal classified with high confidence
- **WHEN** the classification node receives "Move from Berlin to Lisbon within 3 months"
- **THEN** the output includes a domain (e.g., "relocation"), complexity >= 3, confidence >= 0.7, relevant dimensions (e.g., ["timeline", "budget", "housing", "logistics"]), a suggested title (e.g., "Relocate from Berlin to Lisbon"), and language "en"

#### Scenario: Vague goal classified with low confidence
- **WHEN** the classification node receives "be happier"
- **THEN** the output includes confidence < 0.3 and the `dimensions` list is sparse or generic

#### Scenario: Non-English goal language detected
- **WHEN** the classification node receives a goal in Russian (e.g., "Переехать из Берлина в Лиссабон за 3 месяца")
- **THEN** the output includes language "ru", and the suggested_title is in Russian (e.g., "Переезд из Берлина в Лиссабон")

#### Scenario: Language detection for mixed-language input
- **WHEN** the classification node receives input with mixed languages (e.g., "Move to Лиссабон within 3 months")
- **THEN** the output includes the dominant language detected from the input

### Requirement: Board Generation Node
The system SHALL implement a two-step board generation pipeline replacing the single-call board generation node. **Step 1 (Skeleton):** A LangGraph node SHALL generate the board structure from goal context. The skeleton node SHALL receive: the goal's original text, classification output (domain, complexity, dimensions, language), and all Q&A pairs. The skeleton output SHALL conform to a Pydantic schema (`BoardSkeletonOutput`) containing: `board_title` (string), and `tasks` (array of objects each with `id` (string, e.g., "t1"), `title`, `depends_on` (array of task id strings), and `is_goal_node` (boolean, default false)). The output MUST form a valid DAG — no circular dependencies. Tasks with an empty `depends_on` array are root tasks. Exactly one task MUST have `is_goal_node: true`. All generated content (board_title, task titles) SHALL be in the language detected during classification. **Step 2 (Enrichment):** For each task produced by the skeleton, a separate LLM call SHALL generate: `description` (string), `due_date` (nullable ISO date string), `priority` (nullable, one of "low"/"medium"/"high"), `estimated_minutes` (nullable integer), and `subtasks` (array of objects each with `title` (string)). The enrichment output SHALL conform to a Pydantic schema (`TaskEnrichmentOutput`). Enrichment calls SHALL run in parallel with concurrency bounded by a configurable limit (`ai_enrichment_concurrency`, default 5) using `asyncio.Semaphore`. Each enrichment call receives the task title, its dependency and dependent task titles (for context), the full goal context, and the detected language. All generated content SHALL be in the detected language. The enrichment prompts SHALL be stored as a separate module in `prompts/enrich_task.py`. The skeleton prompt SHALL be stored in `prompts/generate_board.py` (updated).

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

#### Scenario: Task enriched with description and metadata
- **WHEN** the enrichment node is called for a task "Research neighborhoods in Lisbon"
- **THEN** the output includes a description (e.g., "Research the best neighborhoods..."), progressive metadata (due_date, priority, estimated_minutes) where relevant, and 2-5 subtasks with titles

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

### Requirement: Board Generation Prompt Module
The board generation skeleton prompt SHALL be stored in `app/domains/ai/prompts/generate_board.py` as a separate module. The prompt SHALL instruct the AI to: design tasks as concrete, actionable steps for achieving the goal; define dependency edges between tasks where one task logically must complete before another can begin; create parallel task paths for independent work streams; create convergence nodes where parallel paths merge into a single milestone task; create exactly one final goal node (with `is_goal_node: true`) that represents the user's original goal, depends on all leaf tasks, and serves as the single sink of the DAG; and ensure the dependency graph forms a valid DAG with no cycles. The prompt SHALL instruct the AI to generate all content in the specified language. The prompt SHALL NOT include instructions about descriptions, metadata, or subtasks — those are handled by the enrichment prompt. The prompt SHALL NOT be inlined in node logic or service functions.

#### Scenario: Board generation skeleton prompt stored separately
- **WHEN** the skeleton node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py`

### Requirement: Board Generation AI Service Function
The AI service layer SHALL expose an async generator function `generate_board_stream(goal)` that accepts a Goal object (with populated `ai_context`), extracts the necessary context (original input, classification including language, questions, answers), and orchestrates the two-step generation with streaming. The function SHALL: (1) invoke the skeleton node with structured output enforcement and DAG validation, (2) yield a `skeleton_ready` event with the skeleton data, (3) run enrichment calls in parallel (bounded by `asyncio.Semaphore(ai_enrichment_concurrency)`), (4) yield a `task_enriched` event as each enrichment completes, (5) yield a `generation_complete` event when all enrichment finishes. If the skeleton generation fails after retries, the function SHALL yield a `generation_error` event. If individual task enrichment fails after retries, the function SHALL continue with other tasks and include failed task IDs in the `generation_complete` event. The function SHALL hide LangGraph internals from callers.

#### Scenario: Service function streams skeleton then enrichments
- **WHEN** `generate_board_stream` is called with an answered goal
- **THEN** the first yielded event is `skeleton_ready` with the board structure, followed by multiple `task_enriched` events (one per task), and finally `generation_complete`

#### Scenario: Service function retries on cyclic skeleton output
- **WHEN** the skeleton node produces a cyclic dependency graph
- **THEN** the function retries the skeleton generation (counting toward the 3-retry limit) before yielding any events

#### Scenario: Service function yields error on total skeleton failure
- **WHEN** the skeleton node fails after all retry attempts
- **THEN** the function yields a `generation_error` event with details about the failure

#### Scenario: Service function continues after single task enrichment failure
- **WHEN** enrichment for one task fails after retries but others succeed
- **THEN** the function yields `task_enriched` for successful tasks and `generation_complete` includes a `failed_tasks` list

## ADDED Requirements

### Requirement: Task Enrichment Prompt Module
The task enrichment prompt SHALL be stored in `app/domains/ai/prompts/enrich_task.py` as a separate module. The prompt SHALL instruct the AI to: write a clear, actionable description for the given task in the context of the overall goal; assign progressive metadata (`due_date`, `priority`, `estimated_minutes`) only when relevant to the task and goal type; generate 2-5 subtasks that break the task into concrete, ordered steps; and produce all content in the specified language. The prompt SHALL receive the task title, its dependency and dependent task titles (for graph context), the goal's original text, classification summary, and the target language code. The prompt SHALL NOT be inlined in node logic or service functions.

#### Scenario: Task enrichment prompt stored separately
- **WHEN** the enrichment node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/enrich_task.py`

#### Scenario: Enrichment prompt includes language instruction
- **WHEN** the enrichment prompt is constructed with language "es"
- **THEN** the prompt includes an instruction to generate all content in Spanish

### Requirement: Language-Aware AI Output
All AI pipeline nodes that produce user-facing text (classification `suggested_title`, question `text` and `options`, board skeleton `board_title` and task `title`, enrichment `description` and subtask `title`) SHALL generate content in the language detected during the classification step. The detected language SHALL be stored as `language` in the goal's `ai_context` JSON alongside the classification data. Each downstream prompt SHALL include an explicit instruction to respond in the detected language, using the ISO 639-1 code and the language's own name (e.g., "Respond in Russian (ru)").

#### Scenario: Russian goal produces Russian board content
- **WHEN** a user inputs a goal in Russian and the classification detects language "ru"
- **THEN** the board title, all task titles, all task descriptions, and all subtask titles are in Russian

#### Scenario: Spanish goal produces Spanish questions
- **WHEN** a user inputs a goal in Spanish and the classification detects language "es"
- **THEN** the adaptive questions (text, options) are generated in Spanish

#### Scenario: English goal remains in English
- **WHEN** a user inputs a goal in English and the classification detects language "en"
- **THEN** all generated content is in English (no behavioral change from current)

### Requirement: Enrichment Concurrency Configuration
The system SHALL add an `ai_enrichment_concurrency` setting (integer, default 5) to the application configuration, read from the `AI_ENRICHMENT_CONCURRENCY` environment variable. This setting controls the maximum number of concurrent LLM calls during the task enrichment step of board generation.

#### Scenario: Default concurrency limit
- **WHEN** the `AI_ENRICHMENT_CONCURRENCY` environment variable is not set
- **THEN** the system uses a default concurrency of 5

#### Scenario: Custom concurrency limit
- **WHEN** `AI_ENRICHMENT_CONCURRENCY` is set to "10"
- **THEN** the system allows up to 10 concurrent enrichment LLM calls

