## ADDED Requirements

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

## MODIFIED Requirements

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
