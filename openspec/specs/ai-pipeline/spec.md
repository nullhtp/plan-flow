# ai-pipeline Specification

## Purpose
AI pipeline for goal understanding and board generation. Covers the LangGraph pipeline with nodes for goal classification (with confidence-based rejection), adaptive question generation (with follow-up rounds), and DAG board generation (flat task list with dependency edges, convergence nodes, and goal node). All nodes use structured output enforcement via Pydantic schemas and OpenRouter LLM gateway.
## Requirements
### Requirement: OpenRouter LLM Client
The system SHALL integrate with OpenRouter (`https://openrouter.ai/api/v1`) via LangChain's `ChatOpenAI` class configured with the OpenRouter base URL. The API key and default model SHALL be read from environment variables (`OPENROUTER_API_KEY`, `AI_DEFAULT_MODEL`). The default model SHALL be `openai/gpt-5.2`. Individual LLM calls SHALL have a 20-second timeout.

#### Scenario: LLM client configured from environment
- **WHEN** the application starts
- **THEN** the LLM client is configured with the OpenRouter API key and model from environment variables

#### Scenario: LLM call timeout
- **WHEN** an LLM call does not respond within 20 seconds
- **THEN** the call is cancelled and an appropriate error is raised

#### Scenario: Missing API key
- **WHEN** the `OPENROUTER_API_KEY` environment variable is not set
- **THEN** the application SHALL fail to start with a clear error message indicating the missing configuration

### Requirement: Goal Classification Node
The system SHALL implement a LangGraph node that classifies a goal from raw text input. The classification output SHALL conform to a Pydantic schema containing: `domain` (string — e.g., "relocation", "learning", "product-launch"), `complexity` (integer 1-5), `confidence` (float 0.0-1.0), `dimensions` (list of strings — key aspects to explore), `suggested_title` (a clean, concise title derived from the raw input), and `language` (string — ISO 639-1 language code detected from the input, e.g., "en", "ru", "es", "de"). The classification prompt SHALL be stored as a separate module in `prompts/classify.py`. The detected language SHALL be stored in the goal's `ai_context` and passed to all downstream pipeline nodes so that all AI-generated content is produced in the user's input language. The classification node SHALL accept an optional `user_context` parameter (formatted string from `format_user_meta_block`) and include it in the user prompt alongside the goal text, enabling time-sensitive and location-aware classification.

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

#### Scenario: Classification uses user context for time-sensitive goals
- **WHEN** the classification node receives "Plan a birthday party for next Saturday" with user_context containing "Current date: 2026-02-19" and "Day of week: Thursday"
- **THEN** the AI MAY factor the current date and proximity into its complexity and dimension analysis

#### Scenario: Classification without user context (backward compatible)
- **WHEN** the classification node receives a goal without user_context (empty string)
- **THEN** classification proceeds normally as before

### Requirement: Confidence-Based Goal Rejection
The system SHALL reject goals whose classification confidence score falls below a configurable threshold (default: 0.3). When a goal is rejected, the classification node SHALL also output a `rejection_reason` (string explaining why the goal is too vague) and `refinement_suggestions` (list of 2-3 concrete, actionable alternative goal descriptions). The rejection output is part of the classification response, not a separate LLM call.

#### Scenario: Goal below confidence threshold is rejected
- **WHEN** the classification node produces a confidence score of 0.15 for "do stuff"
- **THEN** the pipeline marks the goal as rejected, includes a `rejection_reason` (e.g., "This goal is too vague to generate a meaningful plan"), and provides `refinement_suggestions` (e.g., ["Organize my home office in 2 weekends", "Learn basic cooking skills in 1 month"])

#### Scenario: Goal above confidence threshold proceeds to question generation
- **WHEN** the classification node produces a confidence score of 0.8 for "Launch an MVP for my SaaS product"
- **THEN** the pipeline proceeds to the question generation node without rejection

### Requirement: Question Generation Node
The system SHALL implement a LangGraph node that generates 3-7 structured questions based on the classification output. Each question SHALL conform to a Pydantic schema containing: `id` (unique string, e.g., "q1"), `text` (the question), `type` (one of: "text", "select", "multiselect", "number"), `options` (list of 3-6 strings, REQUIRED for all question types), `rationale` (string explaining why this question matters for planning), `required` (boolean, default true), and `allow_other` (boolean, default true — indicates whether the UI should render a free-text "Other" input alongside the options). The `options` field SHALL always be a non-empty list with at least 3 items regardless of question type. For `text` type questions, options SHALL be AI-suggested likely answers. For `number` type questions, options SHALL be meaningful human-readable ranges (e.g., "$1k-5k", "2-3 months", "1-2 rooms"). For `select` and `multiselect` types, options SHALL be relevant choices as before. The question generation prompt SHALL be stored as a separate module in `prompts/questions.py`. When `user_meta` is available in the goal's `ai_context`, the formatted meta context SHALL be appended to the user prompt to enable location-aware, timezone-aware, and device-aware question generation. When memory context is available, the formatted memory block SHALL be appended to the user prompt after the user meta block. The AI SHOULD use memories to avoid asking questions whose answers are already known (e.g., if memory contains "Budget preference: under $5000", the AI MAY skip or pre-fill a budget question). When research context is available (from a lightweight pre-research step), the formatted research context block SHALL be appended to the user prompt after the memory block. The AI SHOULD use research findings to generate more informed, specific questions with realistic options based on current real-world data (e.g., actual price ranges, current regulations, real timelines).

#### Scenario: Questions generated for a relocation goal
- **WHEN** the question generation node receives a classification with domain "relocation" and dimensions ["timeline", "budget", "housing", "logistics"]
- **THEN** the output contains 3-7 questions covering the identified dimensions, each with 3-6 selectable options (e.g., a budget question with options ["Under $5,000", "$5,000-$15,000", "$15,000-$30,000", "$30,000+"], a timeline question with options ["1-2 months", "3-4 months", "5-6 months", "6+ months"])

#### Scenario: Each question includes rationale
- **WHEN** questions are generated for any goal
- **THEN** every question in the output has a non-empty `rationale` field explaining its relevance

#### Scenario: Question count within bounds
- **WHEN** the question generation node produces output
- **THEN** the number of questions is between 3 and 7 inclusive

#### Scenario: All questions have non-empty options
- **WHEN** the question generation node produces output
- **THEN** every question has an `options` list with at least 3 items, regardless of question type

#### Scenario: Text question has suggested answer options
- **WHEN** a question has type "text" (e.g., "What is your main motivation for this move?")
- **THEN** the options list contains 3-6 AI-suggested likely answers (e.g., ["Career opportunity", "Better quality of life", "Family reasons", "Adventure / new experience"])

#### Scenario: Number question has range-based options
- **WHEN** a question has type "number" (e.g., "What is your monthly budget?")
- **THEN** the options list contains 3-6 human-readable ranges (e.g., ["Under $1,000", "$1,000-$2,000", "$2,000-$3,000", "$3,000+"])

#### Scenario: Questions informed by user location
- **WHEN** the question generation node receives a goal with `user_meta.location = { city: "Berlin", country: "Germany" }` and classification domain "relocation"
- **THEN** the generated questions MAY reference the user's current location (e.g., asking about moving FROM Berlin specifically)

#### Scenario: Questions generated without user meta (backward compatible)
- **WHEN** the question generation node receives a goal without `user_meta`
- **THEN** questions are generated normally without location or timezone context

#### Scenario: Questions informed by user memories
- **WHEN** the question generation node receives memory context containing "Budget preference: under $5000" and the classification dimensions include "budget"
- **THEN** the AI MAY skip the budget question or generate a confirmation question instead (e.g., "Last time your budget was under $5000. Is that still the case?")

#### Scenario: Questions generated without memories (backward compatible)
- **WHEN** the question generation node receives no memory context (empty string)
- **THEN** questions are generated normally as if no memories exist

#### Scenario: Questions informed by research context
- **WHEN** the question generation node receives research context containing "Average rent in Lisbon: 800-1500 EUR/month" for a relocation goal
- **THEN** the AI MAY use this data to generate more specific options (e.g., housing budget options based on actual market prices)

#### Scenario: Questions generated without research context (backward compatible)
- **WHEN** the question generation node receives no research context (empty string)
- **THEN** questions are generated normally as if no research was performed

### Requirement: Adaptive Follow-up Question Generation
The system SHALL support generating unlimited rounds of follow-up questions after the user submits initial answers. Each round SHALL generate 2-4 progressively deeper questions based on the full history of previous Q&A rounds. The follow-up generation SHALL reuse the question generation node with additional context: the original classification, all previous rounds of questions and answers (ordered), and the formatted `user_meta` context (when available). The AI SHALL always generate a new batch of questions after each answer submission — the user decides when to stop by clicking "Generate Board". Follow-up questions SHALL have IDs prefixed with the round number (e.g., round 2: "r2q1", "r2q2"; round 3: "r3q1", "r3q2") to distinguish them from initial questions and maintain uniqueness across rounds. The question generation prompt SHALL include explicit instructions to: (a) not repeat topics already covered in previous rounds, (b) drill deeper into partially covered dimensions based on previous answers, (c) explore new dimensions if all current ones are sufficiently covered, and (d) generate 2-4 questions per follow-up round (fewer than the initial 3-7). When the Q&A history exceeds 5 rounds, the system SHALL summarize earlier rounds in the prompt to manage prompt size while preserving essential context.

#### Scenario: Follow-up questions generated after each round
- **WHEN** a user submits answers for any round (including round 1, 2, 3, etc.)
- **THEN** the follow-up generation produces 2-4 new questions that deepen understanding of the goal

#### Scenario: Progressive deepening avoids repetition
- **WHEN** the user has already answered questions about budget and timeline in previous rounds
- **THEN** the new round's questions do NOT ask about budget or timeline again, instead drilling into uncovered dimensions or asking more specific follow-ups on covered topics

#### Scenario: Questions become more specific over rounds
- **WHEN** round 1 asked "What is your budget range?" and the user answered "$5,000-$15,000"
- **AND** round 3 is being generated
- **THEN** the AI MAY ask a more specific question like "How do you want to split the $5,000-$15,000 between housing deposit, moving costs, and initial living expenses?"

#### Scenario: Round-specific question ID prefixes
- **WHEN** follow-up questions are generated for round 4
- **THEN** question IDs are "r4q1", "r4q2", etc.

#### Scenario: Large history summarized in prompt
- **WHEN** the user has completed 6 rounds of Q&A and round 7 is being generated
- **THEN** rounds 1-4 are summarized into a concise context block while rounds 5-6 are included in full detail

#### Scenario: Follow-up generation uses user meta context
- **WHEN** follow-up questions are generated for a goal with `user_meta`
- **THEN** the follow-up generation prompt includes the formatted user context block

### Requirement: Structured Output Enforcement
All LLM calls in the pipeline SHALL use LangChain's `.with_structured_output()` to enforce JSON schema compliance via the corresponding Pydantic models. When the LLM returns output that fails Pydantic validation, the system SHALL automatically retry the same prompt up to 3 times. If all retries fail, the system SHALL raise a structured error that the API layer can translate into a user-friendly error response.

#### Scenario: Valid structured output on first attempt
- **WHEN** the LLM returns valid JSON matching the Pydantic schema
- **THEN** the output is parsed into the Pydantic model and returned without retries

#### Scenario: Malformed output triggers retry
- **WHEN** the LLM returns JSON that fails Pydantic validation
- **THEN** the system retries the same prompt, up to 3 total attempts

#### Scenario: All retries exhausted
- **WHEN** all 3 retry attempts produce invalid output
- **THEN** the system raises an `AIOutputError` with details about the validation failure

### Requirement: LangGraph Pipeline Definition
The system SHALL define a LangGraph `StateGraph` for the goal understanding pipeline with nodes `classify`, `generate_questions`, and `generate_board`. The graph SHALL use a `GoalPipelineState` TypedDict as its state schema. The `GoalPipelineState` SHALL include a `board_generation` field (nullable `BoardGenerationOutput`) for storing the board generation result and a `memory_context` field (string, default empty) for holding the formatted memory block retrieved before pipeline execution. Individual nodes SHALL be defined in `app/domains/ai/nodes/`. All nodes SHALL use a shared LLM factory from `app/domains/ai/llm.py` instead of duplicating LLM instantiation logic. The AI service layer (`app/domains/ai/service.py`) SHALL expose simple async functions (`classify_goal`, `generate_questions`, `generate_follow_up_questions`, `generate_board`) that hide LangGraph internals from callers. The service layer SHALL retrieve relevant memories and pass the formatted memory context to pipeline nodes. Cross-domain types (`BoardSkeletonOutput`, `TaskEnrichmentOutput`) SHALL be imported from `app/core/types.py`.

#### Scenario: Pipeline executes classification then question generation
- **WHEN** the AI service's `classify_goal` function is called with raw goal text
- **THEN** the LangGraph pipeline executes the classify node followed by the generate_questions node (if not rejected) and returns the combined result

#### Scenario: Pipeline short-circuits on rejection
- **WHEN** the classify node produces a confidence score below the rejection threshold
- **THEN** the pipeline does not execute the generate_questions node and returns the rejection result

#### Scenario: Board generation invoked as separate entry point
- **WHEN** the AI service's `generate_board` function is called with a goal
- **THEN** only the generate_board node executes (not the full classify+questions pipeline)

#### Scenario: Memory context available in pipeline state
- **WHEN** the service layer invokes the pipeline for a user with stored memories
- **THEN** the `GoalPipelineState.memory_context` field contains the formatted memory block

#### Scenario: Shared LLM factory used across nodes
- **WHEN** any AI node needs to instantiate a ChatOpenAI client
- **THEN** it imports and calls `get_llm()` from `app/domains/ai/llm.py` instead of defining its own factory

### Requirement: System Prompts as Modules
System prompts for classification, question generation, and board generation SHALL be stored as separate Python modules in `app/domains/ai/prompts/`. Each module SHALL export a string constant or function that returns the prompt. Prompts SHALL NOT be inlined in node logic or service functions.

#### Scenario: Classification prompt stored separately
- **WHEN** the classify node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/classify.py`

#### Scenario: Question generation prompt stored separately
- **WHEN** the generate_questions node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/questions.py`

#### Scenario: Board generation prompt stored separately
- **WHEN** the generate_board node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py`

### Requirement: Board Generation Node
The system SHALL implement a two-step board generation pipeline replacing the single-call board generation node. **Step 1 (Skeleton):** A LangGraph node SHALL generate the board structure from goal context. The skeleton node SHALL receive: the goal's original text, classification output (domain, complexity, dimensions, language), all Q&A pairs, the formatted `user_meta` context (when available), and the formatted research context (when available). The skeleton output SHALL conform to a Pydantic schema (`BoardSkeletonOutput`) containing: `reasoning` (string — chain-of-thought analysis of the task decomposition strategy), `board_title` (string), and `tasks` (array of objects each with `id` (string, e.g., "t1"), `title`, `depends_on` (array of task id strings), and `is_goal_node` (boolean, default false)). The output MUST form a valid DAG — no circular dependencies. Tasks with an empty `depends_on` array are root tasks. Exactly one task MUST have `is_goal_node: true`. All generated content (board_title, task titles) SHALL be in the language detected during classification. **Step 1b (Review):** After the initial skeleton is generated, a review step SHALL critique the skeleton against the research context and optionally produce a revised skeleton. The review executes once (no iterative loop) and does not perform additional web searches. **Step 2 (Enrichment):** For each task produced by the skeleton (or revised skeleton), a separate LLM call SHALL generate: `description` (string), `due_date` (nullable ISO date string), `priority` (nullable, one of "low"/"medium"/"high"), `estimated_minutes` (nullable integer), and `subtasks` (array of objects each with `title` (string)). The enrichment output SHALL conform to a Pydantic schema (`TaskEnrichmentOutput`). Enrichment calls SHALL run in parallel with concurrency bounded by a configurable limit (`ai_enrichment_concurrency`, default 5) using `asyncio.Semaphore`. Each enrichment call receives the task title, its dependency and dependent task titles (for context), the full goal context, the detected language, the formatted `user_meta` context (when available), and the formatted research context (when available). Each enrichment call MAY perform 1-2 additional targeted web searches for task-specific information if research budget remains. All generated content SHALL be in the detected language. The enrichment prompts SHALL be stored as a separate module in `prompts/enrich_task.py`. The skeleton prompt SHALL be stored in `prompts/generate_board.py` (updated). **Step 3 (Subtask Action Generation):** After each task's enrichment is persisted (subtask records exist in the database), a follow-up LLM call SHALL generate actions for the task's subtasks using `generate_subtask_actions`. This call receives the task title, description, status, and the list of subtask titles. The LLM returns action data (label, icon, prompt) for subtasks that can be meaningfully automated, and null for non-automatable subtasks. The generated actions SHALL be persisted on the Subtask records. Action generation failure SHALL NOT block or fail the enrichment — subtasks are created without actions on failure (graceful degradation). Action generation calls SHALL reuse the same concurrency semaphore as enrichment.

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

#### Scenario: Skeleton informed by research context
- **WHEN** the skeleton node receives research context about visa requirements, housing markets, and logistics for a relocation goal
- **THEN** the generated skeleton includes specific tasks informed by the research (e.g., "Apply for NIF tax number" instead of generic "Handle paperwork") and the task ordering reflects real-world dependencies discovered through research

#### Scenario: Skeleton reviewed and revised
- **WHEN** the skeleton is generated and research context reveals missing critical steps
- **THEN** the review step identifies the gaps and produces a revised skeleton that includes the missing tasks while maintaining DAG validity

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

#### Scenario: Enrichment with task-specific research
- **WHEN** enrichment runs for a task "Apply for Portuguese NIF number" and research budget has remaining queries
- **THEN** the enrichment node MAY perform 1-2 targeted searches (e.g., "how to get NIF number Portugal 2026") and incorporate findings into the description and subtasks

#### Scenario: Enrichment without research budget
- **WHEN** enrichment runs for a task but the research budget is exhausted
- **THEN** the enrichment proceeds using only the existing research context without additional searches

### Requirement: Board Generation Prompt Module
The board generation skeleton prompt SHALL be stored in `app/domains/ai/prompts/generate_board.py` as a separate module. The prompt SHALL instruct the AI to: design tasks as concrete, actionable steps for achieving the goal; define dependency edges between tasks where one task logically must complete before another can begin; create parallel task paths for independent work streams; create convergence nodes where parallel paths merge into a single milestone task; create exactly one final goal node (with `is_goal_node: true`) that represents the user's original goal, depends on all leaf tasks, and serves as the single sink of the DAG; and ensure the dependency graph forms a valid DAG with no cycles. The prompt SHALL instruct the AI to generate all content in the specified language. The prompt SHALL NOT include instructions about descriptions, metadata, or subtasks — those are handled by the enrichment prompt. The prompt SHALL NOT be inlined in node logic or service functions.

#### Scenario: Board generation skeleton prompt stored separately
- **WHEN** the skeleton node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py`

### Requirement: Board Generation AI Service Function
The AI service layer SHALL expose an async generator function `generate_board_stream(goal, db_session)` that accepts a Goal object (with populated `ai_context`) and a database session, extracts the necessary context (original input, classification including language, questions, answers, and `user_meta`), retrieves relevant memories for the user, and orchestrates the multi-step generation with streaming. The function SHALL format `user_meta` into a prompt-injectable text block and format retrieved memories into a memory context block, passing both to all generation steps. The function SHALL: (1) retrieve relevant memories via semantic search, (2) run the research node to gather external knowledge (yielding `research_started`, `research_progress`, and `research_complete` SSE events), (3) invoke the skeleton node with research context, structured output enforcement, and DAG validation, (4) run the skeleton review step against research context, (5) yield a `skeleton_ready` event with the (possibly revised) skeleton data, (6) run enrichment calls in parallel (bounded by `asyncio.Semaphore(ai_enrichment_concurrency)`), with each enrichment receiving the research context and optionally performing task-specific searches, (7) yield a `task_enriched` event as each enrichment completes, (8) yield a `generation_complete` event when all enrichment finishes, (9) extract and store memory facts from the completed board generation. If the skeleton generation fails after retries, the function SHALL yield a `generation_error` event. If individual task enrichment fails after retries, the function SHALL continue with other tasks and include failed task IDs in the `generation_complete` event. The function SHALL hide LangGraph internals from callers. Memory extraction after board generation SHALL NOT block the response — it SHALL run as a background task or after yielding the final event. The research budget SHALL be tracked across the entire generation (research node + enrichment searches) using a shared counter.

#### Scenario: Service function streams research then skeleton then enrichments
- **WHEN** `generate_board_stream` is called with an answered goal and Tavily is configured
- **THEN** the yielded events are: `research_started`, one or more `research_progress` events, `research_complete`, `skeleton_ready`, multiple `task_enriched` events, and `generation_complete`

#### Scenario: Service function skips research when Tavily not configured
- **WHEN** `generate_board_stream` is called and `TAVILY_API_KEY` is not set
- **THEN** no research events are yielded and generation proceeds directly to skeleton generation (same as current behavior)

#### Scenario: Service function passes research context to skeleton generation
- **WHEN** `generate_board_stream` is called and research completes with results
- **THEN** the skeleton generation prompt includes the formatted research context block

#### Scenario: Service function passes user meta to skeleton generation
- **WHEN** `generate_board_stream` is called with a goal that has `user_meta` in `ai_context`
- **THEN** the skeleton generation prompt includes the formatted user context block

#### Scenario: Service function passes user meta to enrichment
- **WHEN** `generate_board_stream` is called with a goal that has `user_meta` in `ai_context`
- **THEN** each task enrichment prompt includes the formatted user context block

#### Scenario: Service function retries on cyclic skeleton output
- **WHEN** the skeleton node produces a cyclic dependency graph
- **THEN** the function retries the skeleton generation (counting toward the 3-retry limit) before yielding any events

#### Scenario: Service function yields error on total skeleton failure
- **WHEN** the skeleton node fails after all retry attempts
- **THEN** the function yields a `generation_error` event with details about the failure

#### Scenario: Service function continues after single task enrichment failure
- **WHEN** enrichment for one task fails after retries but others succeed
- **THEN** the function yields `task_enriched` for successful tasks and `generation_complete` includes a `failed_tasks` list

#### Scenario: Service function injects memory context into skeleton
- **WHEN** `generate_board_stream` is called for a user with stored memories
- **THEN** the skeleton generation prompt includes a "Relevant memories from past interactions" section with the most relevant memories

#### Scenario: Service function injects memory context into enrichment
- **WHEN** `generate_board_stream` is called for a user with stored memories
- **THEN** each task enrichment prompt includes the memory context block

#### Scenario: Service function extracts memories after board generation
- **WHEN** board generation completes successfully
- **THEN** memory facts about the generated board (task count, board pattern) are extracted and stored

#### Scenario: Board generation works without memories
- **WHEN** `generate_board_stream` is called for a user with no stored memories
- **THEN** generation proceeds normally without a memory context section in the prompts

#### Scenario: Research budget shared across pipeline stages
- **WHEN** the research node uses 8 queries and the budget is 15
- **THEN** the enrichment phase has 7 remaining queries to distribute across task-specific searches

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

### Requirement: User Meta Prompt Injection
The system SHALL format the `UserMeta` context into a standardized text block and inject it into ALL AI prompts: goal classification, question generation, follow-up question generation, board skeleton generation, task enrichment, task chat, board chat, subtask action generation, and sub-board question generation. The meta block SHALL be formatted with the following fields:

```
User context:
- Timezone: {timezone}
- Locale: {locale}
- Current date: {current_date} (formatted as YYYY-MM-DD from current_datetime)
- Day of week: {day_of_week} (e.g., "Thursday", computed from current date and timezone)
- Location: {city}, {country}
- Device: {device_type}
```

Fields with null values SHALL be omitted from the block. If `location` is null, the "Location" line SHALL be omitted. If `user_meta` is not available at all, the entire "User context" block SHALL be omitted (backward compatible). The formatting function SHALL be implemented as a shared utility in `app/domains/ai/prompts/meta.py`. When a memory context block is also present, the user meta block SHALL appear before the memory context block in the prompt.

The `format_user_meta_block()` function SHALL be extended to compute and include the day-of-week name (in English, e.g., "Monday", "Tuesday") from the current date. A new `resolve_user_context()` function SHALL be added to `prompts/meta.py` that accepts a `user_meta` dict (as stored in `goal.ai_context["user_meta"]`), computes the current date and day-of-week server-side from the server clock adjusted to the stored timezone, and returns the formatted context string. This function SHALL be used by chat endpoints and any call site that needs fresh temporal context without requiring the frontend to send it.

For pipeline calls (question generation, board generation, enrichment), the existing `format_user_meta_block()` SHALL continue to be used with the `current_datetime` provided at goal creation time. For chat endpoints and classification, `resolve_user_context()` SHALL be used to ensure the current date is always accurate.

#### Scenario: Full meta injected into prompt with day of week
- **WHEN** the AI generates a board skeleton for a goal with complete `user_meta` (timezone "Europe/Berlin", locale "de-DE", current_datetime "2026-02-19T14:30:00Z", location { city: "Berlin", country: "Germany" }, device_type "desktop")
- **THEN** the user prompt includes a "User context" section with all six fields including "Day of week: Thursday"

#### Scenario: Meta without location injected into prompt
- **WHEN** the AI generates questions for a goal with `user_meta` that has `location: null`
- **THEN** the user prompt includes a "User context" section with timezone, locale, current date, day of week, and device type, but no "Location" line

#### Scenario: No meta available (backward compatible)
- **WHEN** the AI generates a board skeleton for a goal without `user_meta` in `ai_context`
- **THEN** the user prompt does not include a "User context" section and generation proceeds as before

#### Scenario: Meta and memory blocks ordered correctly
- **WHEN** both user meta and memory context are present in a prompt
- **THEN** the "User context" block appears before the "Relevant memories from past interactions" block

#### Scenario: Server-side date resolution for chat
- **WHEN** a chat endpoint resolves user context from a goal created yesterday with timezone "America/New_York"
- **THEN** the "Current date" reflects today's date in the America/New_York timezone and "Day of week" matches that date

#### Scenario: Day of week computed correctly across timezones
- **WHEN** the server time is 2026-02-20 01:00 UTC and the stored timezone is "Pacific/Auckland" (UTC+13, where it is already 2026-02-20 14:00 Friday)
- **THEN** the context block shows "Current date: 2026-02-20" and "Day of week: Friday"

### Requirement: Board Chat Graph
The system SHALL implement a LangGraph `StateGraph` for board-level AI chat, compiled with the PostgreSQL checkpointer. The graph SHALL share common utilities (should_continue, execute_tools, field extraction) with the task chat graph via `app/domains/ai/graphs/base.py`. The chat graph state SHALL include: `messages` (list of chat messages), `board_id` (string), `user_id` (string), `board_context` (string), `memory_context` (string), `goal_context` (string), and `user_context` (string — formatted user meta block from `resolve_user_context()`). The graph SHALL implement the same ReAct agent loop pattern as the task chat graph. The LLM model SHALL be bound to the board chat tool set via `model.bind_tools(tools)` using tools from the tool registry's `get_board_chat_tools`. The system prompt SHALL instruct the AI about its board-level role. The `respond` node SHALL inject the `user_context` state field into the system prompt via the `{user_context}` template placeholder. Each board's chat session SHALL use a thread ID of format `board-chat-{board_id}`. The graph SHALL be defined in `app/domains/ai/graphs/board_chat.py`. The graph SHALL enforce a maximum of 10 tool-call iterations per turn.

#### Scenario: First message in board chat
- **WHEN** a user sends the first chat message for board "b1" (thread "board-chat-b1")
- **THEN** the graph creates a new thread, injects board context, user context, and memory context, and produces an AI response

#### Scenario: Resuming board chat
- **WHEN** a user sends a second message to a board after a previous conversation
- **THEN** the graph loads the existing thread state from the checkpointer and continues the conversation

#### Scenario: AI uses board structure tool
- **WHEN** a user says "I think we should add a task for getting travel insurance" in board chat
- **THEN** the AI calls `add_task` with appropriate parameters and returns a pending_confirmation result

#### Scenario: AI analyzes board progress
- **WHEN** a user asks "What's my overall progress?" in board chat
- **THEN** the AI calls `get_board_progress`, receives stats, and provides a natural language summary

#### Scenario: AI suggests next actions
- **WHEN** a user asks "What should I work on next?" in board chat
- **THEN** the AI calls `get_blocked_tasks` and `list_all_tasks` to understand the board state, then recommends unlocked tasks based on priority and dependencies

#### Scenario: Shared graph utilities in base module
- **WHEN** the board chat graph needs should_continue or execute_tools logic
- **THEN** it imports these functions from `app/domains/ai/graphs/base.py` rather than reimplementing them

#### Scenario: User context included in board chat
- **WHEN** a user chats about a board and the goal has stored user_meta with timezone "Asia/Tokyo"
- **THEN** the system prompt includes a "User context" block with the current date in the Asia/Tokyo timezone and day of week

### Requirement: Board Chat API Endpoint
The system SHALL expose `POST /api/boards/{board_id}/chat` as an authenticated endpoint that accepts a JSON body with `message` (string). The endpoint SHALL: load the board and its goal context, validate ownership, resolve user context server-side from the goal's stored `user_meta` via `resolve_user_context()`, retrieve relevant memories, obtain the board chat tool set from the tool registry, invoke the board chat graph with the appropriate thread ID and user_context, collect tool actions, and return the enriched chat response conforming to the ChatResponse schema. If the board does not belong to the authenticated user, the endpoint SHALL return 404.

#### Scenario: Successful board chat message
- **WHEN** an authenticated user sends POST /api/boards/{board_id}/chat with body `{"message": "How is the plan looking?"}`
- **THEN** the endpoint returns 200 with the AI's response, tool actions, and thread_id "board-chat-{board_id}"

#### Scenario: Board chat with structural change proposal
- **WHEN** an authenticated user asks the AI to add a task in board chat
- **THEN** the response includes the AI's explanation, a pending_confirmation action, and the pending_action_id

#### Scenario: Unauthorized board access
- **WHEN** a user sends a chat message for another user's board
- **THEN** the endpoint returns 404

#### Scenario: Board not found
- **WHEN** a user sends a chat message for a non-existent board ID
- **THEN** the endpoint returns 404

#### Scenario: Board chat resolves user context from goal
- **WHEN** a user sends a board chat message for a board whose goal has `user_meta` with timezone "Europe/London"
- **THEN** the endpoint resolves the user context server-side with the current date in the Europe/London timezone and passes it to the chat graph

#### Scenario: Board chat without user meta (backward compatible)
- **WHEN** a user sends a board chat message for a board whose goal has no `user_meta`
- **THEN** the endpoint passes an empty string as user_context and chat proceeds normally

### Requirement: AI Chat Model Configuration
The system SHALL add an `AI_CHAT_MODEL` setting (string, default: same as `AI_DEFAULT_MODEL`) to the application configuration. This setting allows using a different model for chat interactions that is optimized for tool calling. The task chat and board chat graphs SHALL use this model instead of the default model.

#### Scenario: Separate chat model configured
- **WHEN** `AI_CHAT_MODEL` is set to "anthropic/claude-sonnet-4"
- **THEN** the task chat and board chat graphs use "anthropic/claude-sonnet-4" for LLM calls

#### Scenario: Chat model defaults to pipeline model
- **WHEN** `AI_CHAT_MODEL` is not set
- **THEN** the chat graphs use the value of `AI_DEFAULT_MODEL`

### Requirement: Tool-Aware Chat System Prompts
The system SHALL maintain separate system prompt modules for task chat (`app/domains/ai/prompts/chat.py`) and board chat (`app/domains/ai/prompts/board_chat.py`). The task chat prompt SHALL instruct the AI on available tools (retrieval, mutations, web search, save_artifact), establish its role as a helpful task assistant, and guide appropriate tool usage. The prompt SHALL include instructions to use the `save_artifact` tool when generating substantial, reusable content such as agreements, plans, research summaries, or comparisons — rather than including long content only in the chat message. The board chat prompt SHALL additionally cover structural tools (add/remove tasks and dependencies, split tasks). Both chat prompts SHALL include a `{user_context}` template placeholder that is populated with the formatted user meta block (from `resolve_user_context()`), enabling the AI to reason about the user's timezone, current date, day of week, locale, location, and device during chat interactions.

#### Scenario: Task chat prompt includes tool instructions
- **WHEN** a task chat graph is compiled
- **THEN** the system prompt from `prompts/chat.py` is used, including instructions for all available tools

#### Scenario: Task chat prompt includes artifact instructions
- **WHEN** the task chat system prompt is loaded
- **THEN** it includes instructions to use `save_artifact` for substantial generated content

#### Scenario: Board chat prompt includes structural tool instructions
- **WHEN** a board chat graph is compiled
- **THEN** the system prompt from `prompts/board_chat.py` is used, including instructions for structural tools

#### Scenario: Task chat prompt includes user context
- **WHEN** a task chat prompt is rendered with user_context containing timezone and current date
- **THEN** the rendered system prompt includes the "User context" block with timezone, date, and day of week

#### Scenario: Board chat prompt includes user context
- **WHEN** a board chat prompt is rendered with user_context containing location "Berlin, Germany"
- **THEN** the rendered system prompt includes the "User context" block with the location

#### Scenario: Chat prompt without user context (backward compatible)
- **WHEN** a chat prompt is rendered with an empty user_context string
- **THEN** the prompt renders without a "User context" section

### Requirement: Action Suggestion Generation
The system SHALL provide an async function `generate_action_suggestions(task_context: str, model: str | None = None) -> list[ActionSuggestion]` in the AI service layer. The function SHALL call the LLM with structured output using the action suggestion prompt and task context string. The function SHALL use the `AI_ACTION_SUGGEST_MODEL` (falling back to `AI_CHAT_MODEL`, then `AI_DEFAULT_MODEL`). The function SHALL return 2–4 `ActionSuggestion` objects. The function SHALL NOT use LangGraph or tools — it is a single structured output LLM call.

#### Scenario: Generate suggestions for a planning task
- **WHEN** `generate_action_suggestions` is called with context for a task titled "Plan team offsite"
- **THEN** it returns 2–4 ActionSuggestion objects with contextual labels and prompts

#### Scenario: Suggestions respect task language
- **WHEN** the task context is in German
- **THEN** the returned suggestions have German labels and prompts

### Requirement: Action Suggestion Prompt Module
The system SHALL store the action suggestion system prompt in `app/domains/ai/prompts/action_suggestions.py`. The prompt SHALL instruct the LLM to: analyze the task's title, description, status, subtasks, and relationships; generate 2–4 diverse action suggestions; use the same language as the task content; produce labels that are short and action-oriented (verb-led); produce prompts that are clear instructions for the task chat AI; and vary the icon categories across suggestions.

#### Scenario: Action suggestion prompt stored as module
- **WHEN** the action suggestion feature loads its prompt
- **THEN** the prompt is imported from `app/domains/ai/prompts/action_suggestions.py`

### Requirement: Subtask Action Generation AI Service Function
The system SHALL provide an async function `generate_subtask_actions(task_title: str, task_description: str, task_status: str, subtasks: list[dict], model: str | None = None) -> list[SubtaskActionOutput]` in the AI service layer. The function SHALL call the LLM with structured output using the subtask action prompt and the task/subtask context. The function SHALL use `AI_ACTION_SUGGEST_MODEL` (falling back to `AI_CHAT_MODEL`, then `AI_DEFAULT_MODEL`). The function SHALL return one `SubtaskActionOutput` per input subtask, with null action fields for non-automatable subtasks. The function SHALL NOT use LangGraph or tools — it is a single structured output LLM call.

#### Scenario: Service function called with task context
- **WHEN** `generate_subtask_actions` is called with task title "Create rental agreement" and subtasks ["Draft agreement terms", "Get notary appointment"]
- **THEN** it returns a list with action data for "Draft agreement terms" and null actions for "Get notary appointment"

#### Scenario: Language matching in service function
- **WHEN** `generate_subtask_actions` is called with German task title and subtask titles
- **THEN** returned action labels and prompts are in German

### Requirement: Subtask Action Prompt Module
The system SHALL store the subtask action system prompt in `app/domains/ai/prompts/action_suggestions.py` (repurposed). The prompt SHALL instruct the LLM to: analyze each subtask in the context of the parent task title, description, and status; determine if AI can meaningfully help with each subtask; generate an action (label, icon, prompt) only for automatable subtasks; return null action fields for subtasks requiring physical presence, manual work, or human interaction; use the same language as the task content; vary action types (icons) across subtasks; write the `prompt` field as a natural instruction that references the specific subtask. The prompt SHALL receive the task title, description, status, a list of subtask titles, and the formatted user context block (when available) to enable time-aware and locale-aware action suggestions.

#### Scenario: Prompt stored as module
- **WHEN** the subtask action generation feature is invoked
- **THEN** the system prompt is loaded from `app/domains/ai/prompts/action_suggestions.py`

#### Scenario: Action suggestions use user context
- **WHEN** subtask action generation receives user_context with "Current date: 2026-02-19" and "Locale: de-DE"
- **THEN** the AI MAY factor date proximity and locale into its action suggestions

### Requirement: Sub-Board Question Generation Node
The system SHALL implement an AI service function `generate_sub_board_questions(task_title: str, task_description: str, board_title: str, goal_context: str, language: str, user_context: str | None = None, memory_context: str | None = None) -> list[QuestionSchema]` that generates 2-4 focused questions for decomposing a task into a sub-board. The function SHALL call the LLM with structured output using a dedicated sub-board question prompt. Each question SHALL conform to the same schema as goal questions (`id`, `text`, `type`, `options`, `rationale`, `required`, `allow_other`). The `options` field SHALL always be a non-empty list with at least 3 items regardless of question type. Question IDs SHALL be prefixed with "sbq" (e.g., "sbq1", "sbq2"). The function SHALL NOT use LangGraph — it is a single structured output LLM call. All generated content SHALL be in the specified language.

#### Scenario: Questions generated for a complex task
- **WHEN** `generate_sub_board_questions` is called with task title "Find and secure housing in Lisbon", task description, board title "Relocation to Lisbon", and goal context
- **THEN** the function returns 2-4 questions focused on housing decomposition, each with 3-6 selectable options (e.g., "What type of housing?" with options ["Studio apartment", "1-bedroom apartment", "Shared flat", "House"])

#### Scenario: Question count within bounds
- **WHEN** `generate_sub_board_questions` produces output
- **THEN** the number of questions is between 2 and 4 inclusive

#### Scenario: All sub-board questions have non-empty options
- **WHEN** `generate_sub_board_questions` produces output
- **THEN** every question has an `options` list with at least 3 items, regardless of question type

#### Scenario: Questions in detected language
- **WHEN** the language parameter is "ru"
- **THEN** all question texts, options, and rationales are in Russian

#### Scenario: Questions informed by user context
- **WHEN** user_context includes location "Berlin, Germany"
- **THEN** the questions MAY reference the user's context where relevant

### Requirement: Sub-Board Question Prompt Module
The system SHALL store the sub-board question generation prompt in `app/domains/ai/prompts/sub_board_questions.py` as a separate module. The prompt SHALL instruct the AI to: analyze the parent task's title and description to understand what needs to be decomposed; consider the broader goal context; generate 2-4 questions that help understand HOW the user wants to approach this specific task; use appropriate field types (text, select, multiselect, number); and produce all content in the specified language. The prompt SHALL emphasize brevity and focus — these are task-specific decomposition questions, not goal-level exploration questions.

#### Scenario: Sub-board question prompt stored as module
- **WHEN** the sub-board question generation needs its prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/sub_board_questions.py`

### Requirement: Sub-Board Skeleton Generation
The system SHALL support generating sub-board skeletons via the existing board generation infrastructure with adjusted parameters. The sub-board skeleton generation SHALL receive: the parent task's title and description, the root board's title and goal context (original input, classification, Q&A pairs), the sub-board question answers, the detected language, user_context, and memory_context. The skeleton output SHALL conform to the same `BoardSkeletonOutput` Pydantic schema but with a task count range of 3-15 (instead of 5-30 for root boards). The generated board title SHALL reflect the parent task (e.g., "Housing Plan" for a "Find and secure housing" parent task). The system SHALL reuse the existing `generate_board_stream` infrastructure, adding a `parent_task_id` parameter to distinguish sub-board generation from root board generation. The sub-board skeleton prompt SHALL be a variant of the board generation prompt, stored in `app/domains/ai/prompts/generate_board.py` as a separate function or constant.

#### Scenario: Sub-board skeleton generated with fewer tasks
- **WHEN** the sub-board skeleton generation is called for a task "Find and secure housing in Lisbon"
- **THEN** the output contains 3-15 tasks with dependency edges forming a valid DAG, a single goal node, and a board title reflecting the parent task

#### Scenario: Sub-board skeleton reuses enrichment pipeline
- **WHEN** a sub-board skeleton is generated
- **THEN** the same parallel enrichment pipeline (with concurrency limits) is used for task enrichment and subtask action generation

#### Scenario: Sub-board skeleton uses parent goal context
- **WHEN** a sub-board is generated for a task on a board whose goal was "Relocate from Berlin to Lisbon"
- **THEN** the skeleton prompt includes the root goal context so the AI understands the broader plan

#### Scenario: Sub-board skeleton prompt stored in generate_board module
- **WHEN** the sub-board skeleton generation needs its prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py` (as a sub-board-specific variant)

### Requirement: Sub-Board AI Service Integration
The AI service layer SHALL expose an async generator function `generate_sub_board_stream(task: Task, board: Board, answers: list[dict], db_session)` that orchestrates sub-board generation. The function SHALL: (1) resolve the root board's goal context (original input, classification, Q&A, language, user_meta) by tracing from the board to the goal, (2) retrieve relevant memories for the user, (3) invoke the sub-board skeleton generation with the adjusted task count range (3-15), (4) yield SSE events in the same format as `generate_board_stream` (skeleton_ready, task_enriched, generation_complete, generation_error), (5) persist the sub-board via the board service with `parent_task_id` set, (6) delete existing subtasks on the parent task before creating the sub-board, (7) auto-transition the parent task to `in_progress` if applicable. The function SHALL reuse existing enrichment and persistence infrastructure.

#### Scenario: Sub-board generation streams events
- **WHEN** `generate_sub_board_stream` is called with a task and answers
- **THEN** it yields `skeleton_ready`, then multiple `task_enriched` events, then `generation_complete` with the sub-board ID

#### Scenario: Sub-board generation resolves root goal context
- **WHEN** `generate_sub_board_stream` is called for a task on a root board
- **THEN** the function resolves the root board's goal and extracts the full AI context (classification, Q&A, language, user_meta)

#### Scenario: Sub-board generation deletes existing subtasks
- **WHEN** `generate_sub_board_stream` is called for a task with 5 existing subtasks
- **THEN** the 5 subtasks are deleted before the sub-board is created

#### Scenario: Sub-board generation auto-starts parent task
- **WHEN** the parent task has status `not_started` and all dependencies are met
- **THEN** the parent task transitions to `in_progress` during sub-board generation

### Requirement: Readiness Assessment
The system SHALL return a readiness assessment alongside each batch of generated questions (both initial and follow-up rounds). The readiness assessment SHALL conform to a Pydantic schema (`ReadinessAssessment`) containing: `score` (float 0.0-1.0 representing overall board generation readiness), `covered_dimensions` (list of strings — dimensions from the classification that are sufficiently covered by collected answers), `uncovered_dimensions` (list of strings — dimensions that still lack information), and `summary` (string — one sentence describing the current readiness state in the detected language). The readiness assessment SHALL be computed as part of the question generation LLM call (not a separate call) by extending the question generation structured output schema to include a `readiness` field. The `score` SHALL reflect the proportion of identified dimensions covered and the quality/specificity of answers. A score of 0.8+ indicates the AI has enough context for a high-quality board. A score below 0.4 indicates significant gaps remain. The assessment SHALL be in the same language as the goal.

#### Scenario: Readiness returned with initial questions
- **WHEN** the question generation node produces initial questions for a relocation goal with dimensions ["timeline", "budget", "housing", "logistics"]
- **THEN** the output includes a readiness assessment with score near 0.0, all dimensions in `uncovered_dimensions`, empty `covered_dimensions`, and a summary like "No answers collected yet. Answer the questions below to improve board quality."

#### Scenario: Readiness improves after answering initial questions
- **WHEN** the follow-up generation runs after the user answered questions about budget and timeline
- **THEN** the readiness assessment includes "budget" and "timeline" in `covered_dimensions`, "housing" and "logistics" in `uncovered_dimensions`, and a score around 0.4-0.6

#### Scenario: High readiness after multiple rounds
- **WHEN** the user has completed 4 rounds covering all classification dimensions thoroughly
- **THEN** the readiness assessment has a score of 0.85+, most dimensions in `covered_dimensions`, and a summary encouraging the user to generate

#### Scenario: Readiness in detected language
- **WHEN** the goal was classified with language "ru"
- **THEN** the readiness `summary` is in Russian

### Requirement: Iterative Question Generation Prompt
The question generation prompt in `app/domains/ai/prompts/questions.py` SHALL be updated to support iterative deepening. The prompt SHALL accept: the classification output, the full Q&A history (all previous rounds), the current round number, the formatted `user_meta` context, and the memory context. The prompt SHALL instruct the AI to: generate 2-4 questions for follow-up rounds (3-7 for the initial round), avoid repeating topics covered in previous rounds, progressively deepen questions based on accumulated answers, include a readiness assessment evaluating dimension coverage, and produce all content in the detected language. The prompt SHALL include a structured section listing which dimensions are covered vs. uncovered based on the Q&A history.

#### Scenario: Initial round prompt generates 3-7 questions
- **WHEN** the question generation prompt is invoked for round 1 (no previous Q&A history)
- **THEN** the prompt instructs the AI to generate 3-7 questions and an initial readiness assessment

#### Scenario: Follow-up round prompt generates 2-4 questions
- **WHEN** the question generation prompt is invoked for round 3 with 2 previous rounds of Q&A
- **THEN** the prompt instructs the AI to generate 2-4 questions that deepen understanding, and the full Q&A history is included in the prompt

#### Scenario: Prompt includes dimension coverage analysis
- **WHEN** the question generation prompt is invoked for any follow-up round
- **THEN** the prompt includes a section listing which classification dimensions are covered by previous answers and which remain uncovered

### Requirement: Research Node
The system SHALL implement a research node in `app/domains/ai/nodes/research.py` that gathers external knowledge before generation pipeline stages. The research node SHALL: (1) accept goal context (raw input, classification output, Q&A answers, user context, memory context), (2) call the LLM with structured output to generate 3-8 search queries relevant to the goal, (3) execute searches in parallel via the shared search utility, (4) deduplicate results by URL, (5) rank results by relevance score, (6) fetch full content from the top N URLs via the URL content extractor, (7) compile all results into a `ResearchContext` object. The research node SHALL track query count against the configurable budget (`AI_MAX_RESEARCH_QUERIES`). When the budget is exhausted, the node SHALL stop generating new queries and proceed with available results. The research node SHALL be defined in `app/domains/ai/nodes/research.py`. All generated search queries SHALL be in the language detected during classification when searching for locale-specific information, and in English when searching for universal/technical information.

#### Scenario: Research for a relocation goal
- **WHEN** the research node receives a goal "Move from Berlin to Lisbon within 3 months" with classification domain "relocation" and dimensions ["timeline", "budget", "housing", "logistics"]
- **THEN** the node generates targeted queries (e.g., "cost of living Lisbon 2026", "Berlin to Lisbon relocation checklist", "Portugal visa requirements EU citizens"), executes them in parallel, and returns a ResearchContext with deduplicated, ranked results

#### Scenario: Research budget respected
- **WHEN** the research node has a budget of 15 queries and the LLM suggests 8 queries for main research
- **THEN** the node executes at most 8 queries for this phase, leaving remaining budget for enrichment

#### Scenario: Research with no Tavily configured
- **WHEN** the research node runs and `TAVILY_API_KEY` is not set
- **THEN** the node returns an empty ResearchContext and the pipeline proceeds without research

#### Scenario: Partial search failures do not block research
- **WHEN** 2 out of 6 search queries fail (timeout or API error)
- **THEN** the node compiles results from the 4 successful queries and continues

#### Scenario: URL content extraction for top results
- **WHEN** the research node has 15 search results after deduplication
- **THEN** the node fetches full content from the top 3-5 URLs (by relevance score) and includes extracted text in the ResearchContext

### Requirement: Research Query Generation Prompt
The system SHALL store the research query generation prompt in `app/domains/ai/prompts/research.py`. The prompt SHALL instruct the LLM to: analyze the goal context (raw input, domain, complexity, dimensions, Q&A answers), generate 3-8 diverse search queries that would provide actionable information for planning, mix locale-specific queries (in the user's language) with universal/technical queries (in English), prioritize queries that fill knowledge gaps not covered by the user's answers, and include a `reasoning` field explaining the research strategy before listing queries. The prompt SHALL NOT be inlined in node logic.

#### Scenario: Research prompt stored separately
- **WHEN** the research node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/research.py`

#### Scenario: Prompt generates diverse query types
- **WHEN** the LLM generates queries for a "Launch a SaaS MVP" goal
- **THEN** queries cover diverse aspects: market research, technical requirements, regulatory, competitive landscape — not just variations of the same topic

### Requirement: Research Context Formatting
The system SHALL provide a `format_research_context()` function in `app/domains/ai/prompts/research.py` that formats a `ResearchContext` object into a prompt-injectable text block. The formatted block SHALL include: a summary header ("Research findings from web search"), each result's title, URL, and a truncated content snippet (max 500 chars per result), and a total result count. The formatted block SHALL be truncated to a configurable maximum length (default 8000 chars) to fit within LLM context windows. When no research results are available, the function SHALL return an empty string.

#### Scenario: Research context formatted for prompt injection
- **WHEN** `format_research_context()` receives a ResearchContext with 10 results
- **THEN** it returns a formatted text block with title, URL, and snippet for each result, truncated to the max length

#### Scenario: Empty research context
- **WHEN** `format_research_context()` receives a ResearchContext with no results
- **THEN** it returns an empty string

### Requirement: URL Content Extraction Utility
The system SHALL provide an async function `fetch_url_content(url: str, max_chars: int = 4000, timeout: float = 10.0) -> str | None` in `app/domains/ai/tools/url_fetch.py`. The function SHALL: (1) fetch the page content via httpx with the specified timeout, (2) extract readable text using a readability extraction library (e.g., `trafilatura`), (3) truncate the extracted text to `max_chars`, (4) return the extracted text or `None` on any failure (timeout, HTTP error, extraction failure). The function SHALL set a realistic User-Agent header. The function SHALL NOT execute JavaScript — it handles static HTML only. Failed fetches SHALL be logged at warning level but SHALL NOT raise exceptions.

#### Scenario: Successful URL content extraction
- **WHEN** `fetch_url_content("https://example.com/article")` is called for a static HTML page
- **THEN** the function returns the readable text content, truncated to 4000 characters

#### Scenario: URL fetch timeout
- **WHEN** `fetch_url_content("https://slow-site.com/page", timeout=5.0)` is called and the server does not respond within 5 seconds
- **THEN** the function returns `None` and logs a warning

#### Scenario: Non-HTML content
- **WHEN** `fetch_url_content` is called for a URL that returns a PDF or image
- **THEN** the function returns `None`

#### Scenario: JavaScript-rendered page
- **WHEN** `fetch_url_content` is called for a page that requires JavaScript to render content
- **THEN** the function returns whatever static HTML content is available, which may be minimal or empty

### Requirement: Shared Search Utility
The system SHALL provide an async function `execute_search(query: str, max_results: int = 5) -> list[SearchResult]` in `app/domains/ai/research.py` that wraps the Tavily API for use by pipeline nodes (not a LangChain tool). The function SHALL return a list of `SearchResult` objects (with `title`, `url`, `content`, `score` fields). When `TAVILY_API_KEY` is not configured, the function SHALL return an empty list. On API failure, the function SHALL log a warning and return an empty list. The function SHALL be importable by any pipeline node without requiring LangChain tool infrastructure.

#### Scenario: Successful search
- **WHEN** `execute_search("apartment rental prices Lisbon 2026")` is called with Tavily configured
- **THEN** the function returns up to 5 SearchResult objects with titles, URLs, content snippets, and scores

#### Scenario: Search without Tavily configured
- **WHEN** `execute_search` is called and `TAVILY_API_KEY` is not set
- **THEN** the function returns an empty list

#### Scenario: Search API failure
- **WHEN** the Tavily API returns an error
- **THEN** the function logs a warning and returns an empty list

### Requirement: Research Output Schemas
The system SHALL define the following Pydantic schemas in `app/domains/ai/schemas.py`: `ResearchQueriesOutput` containing `reasoning` (string — chain-of-thought explanation of research strategy) and `queries` (list of strings — 3-8 search queries); `SearchResult` containing `title` (string), `url` (string), `content` (string — snippet or extracted text), and `score` (float — relevance score); `ResearchContext` containing `results` (list of SearchResult), `queries_used` (int — number of queries executed), and `budget_remaining` (int — queries left in budget).

#### Scenario: Research queries output validated
- **WHEN** the LLM returns research query output
- **THEN** it is parsed into a `ResearchQueriesOutput` with a reasoning string and 3-8 query strings

#### Scenario: Research context tracks budget
- **WHEN** a ResearchContext is created after 6 queries with a budget of 15
- **THEN** `queries_used` is 6 and `budget_remaining` is 9

### Requirement: Skeleton Revision Step
The system SHALL implement a skeleton review function in `app/domains/ai/nodes/generate_board.py` that reviews the generated skeleton against the gathered research context and optionally revises it. The review function SHALL: (1) receive the initial skeleton, research context, goal context (raw input, classification, Q&A answers), and memory context, (2) call the LLM with structured output to produce a `SkeletonReviewOutput` containing `reasoning` (string — analysis of the skeleton), `issues` (list of strings — problems found), `has_issues` (boolean), and optionally `revised_skeleton` (a complete `BoardSkeletonOutput` replacing the original), (3) if `has_issues` is true and `revised_skeleton` is provided, replace the original skeleton with the revision, (4) validate the revised skeleton against DAG rules. The review step SHALL NOT perform additional web searches — it uses only the research context already gathered. The review step SHALL execute only once (no iterative loop). The revision prompt SHALL be stored in `app/domains/ai/prompts/review_skeleton.py`.

#### Scenario: Skeleton passes review without changes
- **WHEN** the review step receives a well-formed skeleton that covers all key aspects from the research context
- **THEN** `has_issues` is false, `issues` is empty, `revised_skeleton` is null, and the original skeleton is kept

#### Scenario: Skeleton revised based on research gaps
- **WHEN** the review step receives a skeleton for "Move to Portugal" and the research context mentions visa requirements, but the skeleton has no visa-related tasks
- **THEN** `has_issues` is true, `issues` includes "Missing visa/immigration tasks", and `revised_skeleton` includes visa-related tasks while maintaining DAG validity

#### Scenario: Revised skeleton validated
- **WHEN** the review step produces a revised skeleton
- **THEN** the revised skeleton is validated for DAG correctness (no cycles, exactly one goal node) before replacing the original

#### Scenario: Invalid revision falls back to original
- **WHEN** the review step produces a revised skeleton that fails DAG validation
- **THEN** the original skeleton is kept and a warning is logged

### Requirement: Skeleton Review Prompt Module
The system SHALL store the skeleton review prompt in `app/domains/ai/prompts/review_skeleton.py`. The prompt SHALL instruct the LLM to: analyze the generated skeleton against the gathered research context, identify missing critical steps that the research suggests are necessary, identify tasks that are too vague or could be split, check that the task ordering and dependencies make practical sense, produce a `reasoning` field with chain-of-thought analysis, and produce a revised skeleton only if significant issues are found (not for minor wording improvements). The prompt SHALL NOT be inlined in node logic.

#### Scenario: Review prompt stored separately
- **WHEN** the review step needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/review_skeleton.py`

### Requirement: Research Configuration
The system SHALL add the following settings to the application configuration: `AI_MAX_RESEARCH_QUERIES` (integer, default: 15) — maximum total web search queries per board generation, enforced by the research node; `AI_MAX_FETCH_URLS` (integer, default: 5) — maximum number of URLs to fetch full content from per research phase; `AI_RESEARCH_CONTEXT_MAX_CHARS` (integer, default: 8000) — maximum character length of the formatted research context block injected into prompts. All settings SHALL be read from environment variables.

#### Scenario: Default research budget
- **WHEN** the `AI_MAX_RESEARCH_QUERIES` environment variable is not set
- **THEN** the system uses a default budget of 15 queries per generation

#### Scenario: Custom research budget
- **WHEN** `AI_MAX_RESEARCH_QUERIES` is set to "8"
- **THEN** the research node stops after 8 total queries across all pipeline stages

#### Scenario: Research disabled via zero budget
- **WHEN** `AI_MAX_RESEARCH_QUERIES` is set to "0"
- **THEN** no web searches are performed during generation (equivalent to no Tavily key)

### Requirement: Chain-of-Thought Reasoning in Structured Output
All pipeline nodes that use structured output (classification, question generation, board skeleton, task enrichment, research query generation, skeleton review) SHALL include a `reasoning` field (string) in their Pydantic output schemas. The corresponding prompts SHALL instruct the LLM to use this field to think through its approach step-by-step before producing the actual structured output. The `reasoning` field SHALL be logged for debugging and monitoring but SHALL NOT be sent to the frontend or included in API responses. Existing schemas (`ClassificationOutput`, `QuestionsOutput`, `BoardSkeletonOutput`, `TaskEnrichmentOutput`) SHALL be extended with the `reasoning` field as an optional string (default empty string) to maintain backward compatibility.

#### Scenario: Classification includes reasoning
- **WHEN** the classification node produces output for "Start a podcast about AI"
- **THEN** the `reasoning` field contains the LLM's analysis (e.g., "This is a creative/media goal. Complexity is moderate — requires equipment, content planning, and distribution. Key dimensions are content strategy, technical setup, audience, and monetization.")

#### Scenario: Board skeleton includes reasoning
- **WHEN** the skeleton node produces output for a relocation goal
- **THEN** the `reasoning` field contains analysis of the task decomposition strategy (e.g., "This is a complex relocation requiring parallel tracks: administrative/legal, housing, logistics, and settling in. I'll create convergence points at key milestones.")

#### Scenario: Reasoning field is optional for backward compatibility
- **WHEN** an LLM response does not include the `reasoning` field
- **THEN** the Pydantic schema defaults it to an empty string and parsing succeeds

### Requirement: Few-Shot Examples in Generation Prompts
The classification, question generation, board skeleton, and task enrichment prompts SHALL each include 1-2 few-shot examples of high-quality output. Few-shot examples SHALL be stored as constants within the respective prompt modules (not in separate files). The classification prompt SHALL include an example showing a well-classified goal with appropriate dimensions and confidence. The question generation prompt SHALL include an example showing well-structured questions with diverse types and relevant options. The board skeleton prompt SHALL include an example showing a well-formed DAG with parallel paths, convergence nodes, and a goal node. The enrichment prompt SHALL include an example showing a well-enriched task with progressive metadata and actionable subtasks.

#### Scenario: Classification prompt includes example
- **WHEN** the classification prompt is loaded
- **THEN** it contains at least one example of a classified goal (input + expected output structure)

#### Scenario: Skeleton prompt includes DAG example
- **WHEN** the skeleton generation prompt is loaded
- **THEN** it contains at least one example of a valid task DAG with dependencies, parallel paths, and a goal node

#### Scenario: Few-shot examples are in the prompt module
- **WHEN** the enrichment prompt needs few-shot examples
- **THEN** the examples are defined as constants in `prompts/enrich_task.py`, not in separate files

### Requirement: Pre-Research for Question Generation
The AI service layer SHALL perform a lightweight pre-research step (1-2 web searches) before question generation when Tavily is configured. The pre-research SHALL use the goal's raw input and classification output to generate 1-2 targeted search queries, execute them, and format the results into a research context block. This research context SHALL be passed to the question generation node alongside user meta and memory context. The pre-research SHALL NOT count against the main generation research budget (`AI_MAX_RESEARCH_QUERIES`) — it uses a separate fixed allowance of 2 queries. When Tavily is not configured, the pre-research step SHALL be skipped and questions are generated as before.

#### Scenario: Pre-research improves question quality
- **WHEN** the service layer generates questions for a "Move to Lisbon" goal with Tavily configured
- **THEN** 1-2 search queries are executed (e.g., "moving to Lisbon from Germany requirements 2026"), and the research findings are included in the question generation prompt

#### Scenario: Pre-research skipped when Tavily not configured
- **WHEN** the service layer generates questions and `TAVILY_API_KEY` is not set
- **THEN** questions are generated without any pre-research (backward compatible)

#### Scenario: Pre-research does not affect main research budget
- **WHEN** pre-research executes 2 queries and the main research budget is 15
- **THEN** the main generation research node still has 15 queries available

