## ADDED Requirements

### Requirement: Template Classification AI Service Function
The AI service layer SHALL expose an async function `classify_template_content(content: str, input_type: str, title: str | None, user_id: UUID, db_session: AsyncSession) -> TemplateClassificationResult` that classifies template input and generates initial questions. The function SHALL reuse the goal classification pipeline: (1) run the classification node on the content to detect domain, complexity, confidence, dimensions, and language, (2) generate 3-7 questions based on the classification, adapted for template context. For content-based inputs (`text`, `file`, `url`), the classification prompt SHALL include instructions to analyze the provided content and generate questions that clarify template scope and customization (e.g., team size, budget scope, depth of detail). For `describe` inputs, the classification SHALL work identically to goal classification. The function SHALL return a `TemplateClassificationResult` containing classification data, questions, and a session identifier. The classification prompt for templates SHALL be stored in `app/domains/ai/prompts/generate_template_questions.py`.

#### Scenario: Classify description input
- **WHEN** `classify_template_content` is called with `input_type="describe"` and content "Wedding planning template"
- **THEN** it returns a classification with domain "events", relevant dimensions, language "en", and 3-7 questions about template scope

#### Scenario: Classify extracted content
- **WHEN** `classify_template_content` is called with `input_type="text"` and extracted project plan content
- **THEN** it returns a classification based on content analysis and questions clarifying how to structure the template

### Requirement: Template Follow-up Question Generation
The AI service layer SHALL expose an async function `generate_template_follow_up_questions(classification: dict, rounds: list[dict], source_content: str | None) -> TemplateFollowUpResult` that generates one follow-up round of 2-4 questions based on the classification and previous Q&A round. The function SHALL reuse the follow-up question generation logic from the goal pipeline, adapted for template context. The function SHALL also compute a readiness assessment (score 0-1, summary, covered/uncovered dimensions). The function SHALL enforce a maximum of 1 follow-up round — callers are responsible for not requesting more.

#### Scenario: Generate follow-up questions after round 1
- **WHEN** `generate_template_follow_up_questions` is called with classification and round 1 Q&A
- **THEN** it returns 2-4 deeper questions that don't repeat round 1 topics, plus a readiness score

#### Scenario: Readiness assessment reflects coverage
- **WHEN** the Q&A covers 3 of 5 identified dimensions
- **THEN** the readiness score is approximately 0.5-0.7 with covered and uncovered dimensions listed

### Requirement: Template Generation Streaming Pipeline
The AI service layer SHALL expose an async generator function `generate_template_stream(classification: dict, rounds: list[dict], source_content: str | None, title: str | None, user_id: UUID, db_session: AsyncSession)` that orchestrates multi-step template generation with streaming, mirroring the board generation pipeline. The function SHALL: (1) optionally run research via Tavily (yielding `research_started`, `research_progress`, `research_complete` events), (2) generate a skeleton using template-specific prompts that incorporate the classification, Q&A context, and source content (yielding `skeleton_ready`), (3) run a skeleton review step, (4) run parallel task enrichment bounded by `asyncio.Semaphore(ai_enrichment_concurrency)` (yielding `task_enriched` per task), (5) yield `generation_complete` with the full template structure. The template skeleton prompt SHALL instruct the AI to generate reusable, generic tasks (not personal/specific) suitable for a template. The function SHALL use the same structured output schemas (`BoardSkeletonOutput`, `TaskEnrichmentOutput`) as board generation. If skeleton generation fails after retries, the function SHALL yield `generation_error`.

#### Scenario: Full pipeline with research
- **WHEN** `generate_template_stream` is called with Tavily configured
- **THEN** events yielded are: `research_started`, `research_progress` events, `research_complete`, `skeleton_ready`, `task_enriched` events, `generation_complete`

#### Scenario: Pipeline without research
- **WHEN** `generate_template_stream` is called without Tavily
- **THEN** events yielded are: `skeleton_ready`, `task_enriched` events, `generation_complete`

#### Scenario: Skeleton uses Q&A context and source content
- **WHEN** the skeleton is generated for a template with source content from a PDF and 2 rounds of Q&A
- **THEN** the skeleton prompt includes both the source content and Q&A pairs as context

#### Scenario: Skeleton generates reusable tasks
- **WHEN** the template skeleton is generated from description "Sprint planning template"
- **THEN** tasks are generic and reusable (e.g., "Define sprint goals" not "Define Q3 revenue sprint goals")

#### Scenario: Enrichment failure does not block others
- **WHEN** enrichment for one task fails but others succeed
- **THEN** the `generation_complete` event includes `failed_tasks` list

### Requirement: Template Generation Prompt Module
The template generation prompt for the classification and question generation steps SHALL be stored in `app/domains/ai/prompts/generate_template_questions.py` as a separate module. The prompt SHALL instruct the AI to: analyze the input content or description for template generation (not personal goal planning), identify key dimensions relevant to template customization (team size, scope, industry, depth of detail), detect the domain and language, and generate questions that help refine the template structure. The prompt SHALL NOT be inlined in service functions.

#### Scenario: Template question prompt stored separately
- **WHEN** the template classification and question generation needs its prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_template_questions.py`

### Requirement: Template Skeleton Prompt Module
The template skeleton generation prompt SHALL be stored in `app/domains/ai/prompts/generate_template_skeleton.py` as a separate module. The prompt SHALL instruct the AI to: design tasks as reusable, generic steps suitable for a template (not personalized to a specific user), incorporate source content structure when available, respect the Q&A customization preferences, define dependency edges forming a valid DAG with one goal node, and generate all content in the detected language. The prompt SHALL NOT be inlined in service functions.

#### Scenario: Template skeleton prompt stored separately
- **WHEN** the template skeleton generation needs its prompt
- **THEN** it imports the prompt from `app/domains/ai/prompts/generate_template_skeleton.py`
