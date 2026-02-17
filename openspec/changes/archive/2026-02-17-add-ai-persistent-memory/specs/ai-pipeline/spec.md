## MODIFIED Requirements

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

### Requirement: LangGraph Pipeline Definition
The system SHALL define a LangGraph `StateGraph` for the goal understanding pipeline with nodes `classify`, `generate_questions`, and `generate_board`. The graph SHALL use a `GoalPipelineState` TypedDict as its state schema. The `GoalPipelineState` SHALL include a `board_generation` field (nullable `BoardGenerationOutput`) for storing the board generation result and a `memory_context` field (string, default empty) for holding the formatted memory block retrieved before pipeline execution. The pipeline SHALL be defined in `app/domains/ai/pipeline.py` and individual nodes in `app/domains/ai/nodes/`. The AI service layer (`app/domains/ai/service.py`) SHALL expose simple async functions (`classify_goal`, `generate_questions`, `generate_follow_up_questions`, `generate_board`) that hide LangGraph internals from callers. The service layer SHALL retrieve relevant memories and pass the formatted memory context to pipeline nodes.

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
