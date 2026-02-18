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

### Requirement: Confidence-Based Goal Rejection
The system SHALL reject goals whose classification confidence score falls below a configurable threshold (default: 0.3). When a goal is rejected, the classification node SHALL also output a `rejection_reason` (string explaining why the goal is too vague) and `refinement_suggestions` (list of 2-3 concrete, actionable alternative goal descriptions). The rejection output is part of the classification response, not a separate LLM call.

#### Scenario: Goal below confidence threshold is rejected
- **WHEN** the classification node produces a confidence score of 0.15 for "do stuff"
- **THEN** the pipeline marks the goal as rejected, includes a `rejection_reason` (e.g., "This goal is too vague to generate a meaningful plan"), and provides `refinement_suggestions` (e.g., ["Organize my home office in 2 weekends", "Learn basic cooking skills in 1 month"])

#### Scenario: Goal above confidence threshold proceeds to question generation
- **WHEN** the classification node produces a confidence score of 0.8 for "Launch an MVP for my SaaS product"
- **THEN** the pipeline proceeds to the question generation node without rejection

### Requirement: Question Generation Node
The system SHALL implement a LangGraph node that generates 3-7 structured questions based on the classification output. Each question SHALL conform to a Pydantic schema containing: `id` (unique string, e.g., "q1"), `text` (the question), `type` (one of: "text", "select", "multiselect", "number"), `options` (list of strings, required for select/multiselect, null for text/number), `rationale` (string explaining why this question matters for planning), and `required` (boolean, default true). The question generation prompt SHALL be stored as a separate module in `prompts/questions.py`. When `user_meta` is available in the goal's `ai_context`, the formatted meta context SHALL be appended to the user prompt to enable location-aware, timezone-aware, and device-aware question generation. When memory context is available, the formatted memory block SHALL be appended to the user prompt after the user meta block. The AI SHOULD use memories to avoid asking questions whose answers are already known (e.g., if memory contains "Budget preference: under $5000", the AI MAY skip or pre-fill a budget question).

#### Scenario: Questions generated for a relocation goal
- **WHEN** the question generation node receives a classification with domain "relocation" and dimensions ["timeline", "budget", "housing", "logistics"]
- **THEN** the output contains 3-7 questions covering the identified dimensions, each with appropriate field types (e.g., a budget question might be type "select" with predefined ranges, a timeline question might be type "text")

#### Scenario: Each question includes rationale
- **WHEN** questions are generated for any goal
- **THEN** every question in the output has a non-empty `rationale` field explaining its relevance

#### Scenario: Question count within bounds
- **WHEN** the question generation node produces output
- **THEN** the number of questions is between 3 and 7 inclusive

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

### Requirement: Adaptive Follow-up Question Generation
The system SHALL support generating up to 1 round of follow-up questions after the user submits initial answers. The follow-up generation reuses the question generation node with additional context: the original classification, the initial questions, the user's answers, and the formatted `user_meta` context (when available). The AI SHALL decide whether follow-ups are needed — it MAY return an empty list if the initial answers are sufficient. Follow-up questions SHALL have IDs prefixed with "fq" (e.g., "fq1") to distinguish them from initial questions.

#### Scenario: Follow-up questions generated when answers reveal gaps
- **WHEN** a user answers initial questions for a relocation goal and indicates they have pets
- **AND** no initial question addressed pet relocation
- **THEN** the follow-up generation MAY produce additional questions about pet transport requirements

#### Scenario: No follow-ups when answers are comprehensive
- **WHEN** a user provides thorough answers to all initial questions
- **THEN** the follow-up generation returns an empty question list

#### Scenario: Maximum one follow-up round enforced
- **WHEN** the system has already generated one round of follow-up questions
- **AND** the user submits follow-up answers
- **THEN** no additional follow-up generation occurs regardless of answer content

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
The system SHALL implement a two-step board generation pipeline replacing the single-call board generation node. **Step 1 (Skeleton):** A LangGraph node SHALL generate the board structure from goal context. The skeleton node SHALL receive: the goal's original text, classification output (domain, complexity, dimensions, language), all Q&A pairs, and the formatted `user_meta` context (when available). The skeleton output SHALL conform to a Pydantic schema (`BoardSkeletonOutput`) containing: `board_title` (string), and `tasks` (array of objects each with `id` (string, e.g., "t1"), `title`, `depends_on` (array of task id strings), and `is_goal_node` (boolean, default false)). The output MUST form a valid DAG — no circular dependencies. Tasks with an empty `depends_on` array are root tasks. Exactly one task MUST have `is_goal_node: true`. All generated content (board_title, task titles) SHALL be in the language detected during classification. **Step 2 (Enrichment):** For each task produced by the skeleton, a separate LLM call SHALL generate: `description` (string), `due_date` (nullable ISO date string), `priority` (nullable, one of "low"/"medium"/"high"), `estimated_minutes` (nullable integer), and `subtasks` (array of objects each with `title` (string)). The enrichment output SHALL conform to a Pydantic schema (`TaskEnrichmentOutput`). Enrichment calls SHALL run in parallel with concurrency bounded by a configurable limit (`ai_enrichment_concurrency`, default 5) using `asyncio.Semaphore`. Each enrichment call receives the task title, its dependency and dependent task titles (for context), the full goal context, the detected language, and the formatted `user_meta` context (when available). All generated content SHALL be in the detected language. The enrichment prompts SHALL be stored as a separate module in `prompts/enrich_task.py`. The skeleton prompt SHALL be stored in `prompts/generate_board.py` (updated).

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

### Requirement: Board Generation Prompt Module
The board generation skeleton prompt SHALL be stored in `app/domains/ai/prompts/generate_board.py` as a separate module. The prompt SHALL instruct the AI to: design tasks as concrete, actionable steps for achieving the goal; define dependency edges between tasks where one task logically must complete before another can begin; create parallel task paths for independent work streams; create convergence nodes where parallel paths merge into a single milestone task; create exactly one final goal node (with `is_goal_node: true`) that represents the user's original goal, depends on all leaf tasks, and serves as the single sink of the DAG; and ensure the dependency graph forms a valid DAG with no cycles. The prompt SHALL instruct the AI to generate all content in the specified language. The prompt SHALL NOT include instructions about descriptions, metadata, or subtasks — those are handled by the enrichment prompt. The prompt SHALL NOT be inlined in node logic or service functions.

#### Scenario: Board generation skeleton prompt stored separately
- **WHEN** the skeleton node needs its system prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_board.py`

### Requirement: Board Generation AI Service Function
The AI service layer SHALL expose an async generator function `generate_board_stream(goal, db_session)` that accepts a Goal object (with populated `ai_context`) and a database session, extracts the necessary context (original input, classification including language, questions, answers, and `user_meta`), retrieves relevant memories for the user, and orchestrates the two-step generation with streaming. The function SHALL format `user_meta` into a prompt-injectable text block and format retrieved memories into a memory context block, passing both to skeleton and enrichment calls. The function SHALL: (1) retrieve relevant memories via semantic search, (2) invoke the skeleton node with structured output enforcement and DAG validation, (3) yield a `skeleton_ready` event with the skeleton data, (4) run enrichment calls in parallel (bounded by `asyncio.Semaphore(ai_enrichment_concurrency)`), (5) yield a `task_enriched` event as each enrichment completes, (6) yield a `generation_complete` event when all enrichment finishes, (7) extract and store memory facts from the completed board generation. If the skeleton generation fails after retries, the function SHALL yield a `generation_error` event. If individual task enrichment fails after retries, the function SHALL continue with other tasks and include failed task IDs in the `generation_complete` event. The function SHALL hide LangGraph internals from callers. Memory extraction after board generation SHALL NOT block the response — it SHALL run as a background task or after yielding the final event.

#### Scenario: Service function streams skeleton then enrichments
- **WHEN** `generate_board_stream` is called with an answered goal
- **THEN** the first yielded event is `skeleton_ready` with the board structure, followed by multiple `task_enriched` events (one per task), and finally `generation_complete`

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
The system SHALL format the `UserMeta` context into a standardized text block and inject it into AI prompts for question generation, follow-up question generation, board skeleton generation, task enrichment, and task chat. The meta block SHALL be appended to the user prompt (not the system prompt) with the following format:

```
User context:
- Timezone: {timezone}
- Locale: {locale}
- Current date: {current_date} (formatted as YYYY-MM-DD from current_datetime)
- Location: {city}, {country}
- Device: {device_type}
```

Fields with null values SHALL be omitted from the block. If `location` is null, the "Location" line SHALL be omitted. If `user_meta` is not available at all, the entire "User context" block SHALL be omitted (backward compatible). The formatting function SHALL be implemented as a shared utility in the AI domain (e.g., `app/domains/ai/prompts/meta.py` or a helper in `app/domains/ai/service.py`). When a memory context block is also present, the user meta block SHALL appear before the memory context block in the prompt.

#### Scenario: Full meta injected into prompt
- **WHEN** the AI generates a board skeleton for a goal with complete `user_meta` (timezone "Europe/Berlin", locale "de-DE", current_datetime "2026-02-17T14:30:00Z", location { city: "Berlin", country: "Germany" }, device_type "desktop")
- **THEN** the user prompt includes a "User context" section with all five fields

#### Scenario: Meta without location injected into prompt
- **WHEN** the AI generates questions for a goal with `user_meta` that has `location: null`
- **THEN** the user prompt includes a "User context" section with timezone, locale, current date, and device type, but no "Location" line

#### Scenario: No meta available (backward compatible)
- **WHEN** the AI generates a board skeleton for a goal without `user_meta` in `ai_context`
- **THEN** the user prompt does not include a "User context" section and generation proceeds as before

#### Scenario: Meta and memory blocks ordered correctly
- **WHEN** both user meta and memory context are present in a prompt
- **THEN** the "User context" block appears before the "Relevant memories from past interactions" block

### Requirement: Board Chat Graph
The system SHALL implement a LangGraph `StateGraph` for board-level AI chat, compiled with the PostgreSQL checkpointer. The graph SHALL share common utilities (should_continue, execute_tools, field extraction) with the task chat graph via `app/domains/ai/graphs/base.py`. The chat graph state SHALL include: `messages` (list of chat messages), `board_id` (string), `user_id` (string), `board_context` (string), `memory_context` (string), and `goal_context` (string). The graph SHALL implement the same ReAct agent loop pattern as the task chat graph. The LLM model SHALL be bound to the board chat tool set via `model.bind_tools(tools)` using tools from the tool registry's `get_board_chat_tools`. The system prompt SHALL instruct the AI about its board-level role. Each board's chat session SHALL use a thread ID of format `board-chat-{board_id}`. The graph SHALL be defined in `app/domains/ai/graphs/board_chat.py`. The graph SHALL enforce a maximum of 10 tool-call iterations per turn.

#### Scenario: First message in board chat
- **WHEN** a user sends the first chat message for board "b1" (thread "board-chat-b1")
- **THEN** the graph creates a new thread, injects board context and memory context, and produces an AI response

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

### Requirement: Board Chat API Endpoint
The system SHALL expose `POST /api/boards/{board_id}/chat` as an authenticated endpoint that accepts a JSON body with `message` (string). The endpoint SHALL: load the board and its goal context, validate ownership, retrieve relevant memories, obtain the board chat tool set from the tool registry, invoke the board chat graph with the appropriate thread ID, collect tool actions, and return the enriched chat response conforming to the ChatResponse schema. If the board does not belong to the authenticated user, the endpoint SHALL return 404.

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

### Requirement: AI Chat Model Configuration
The system SHALL add an `AI_CHAT_MODEL` setting (string, default: same as `AI_DEFAULT_MODEL`) to the application configuration. This setting allows using a different model for chat interactions that is optimized for tool calling. The task chat and board chat graphs SHALL use this model instead of the default model.

#### Scenario: Separate chat model configured
- **WHEN** `AI_CHAT_MODEL` is set to "anthropic/claude-sonnet-4"
- **THEN** the task chat and board chat graphs use "anthropic/claude-sonnet-4" for LLM calls

#### Scenario: Chat model defaults to pipeline model
- **WHEN** `AI_CHAT_MODEL` is not set
- **THEN** the chat graphs use the value of `AI_DEFAULT_MODEL`

### Requirement: Tool-Aware Chat System Prompts
The system SHALL update the task chat system prompt and create a board chat system prompt that instruct the AI about tool usage. The prompts SHALL be stored in `app/domains/ai/prompts/chat.py` (updated) and `app/domains/ai/prompts/board_chat.py` (new). The prompts SHALL instruct the AI to: (1) use tools proactively when they can help answer the user's question or fulfill their request, (2) prefer reading board state via tools over making assumptions, (3) explain what it's doing when using tools, (4) clearly communicate when an action requires user confirmation, (5) use web search only when the user asks for research or when external info is genuinely needed, and (6) never fabricate tool results.

#### Scenario: Task chat prompt includes tool instructions
- **WHEN** the task chat system prompt is constructed
- **THEN** it includes instructions about available tools, when to use them, and confirmation behavior

#### Scenario: Board chat prompt includes structural tool instructions
- **WHEN** the board chat system prompt is constructed
- **THEN** it includes instructions about board-wide tools including adding/removing tasks and managing dependencies

