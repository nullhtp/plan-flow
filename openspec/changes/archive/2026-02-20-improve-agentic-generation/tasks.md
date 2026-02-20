## 1. Research Infrastructure
- [x] 1.1 Add `trafilatura` (or chosen readability lib) to backend dependencies
- [x] 1.2 Create `app/domains/ai/tools/url_fetch.py` — async URL fetcher with content extraction, timeout handling, and character truncation
- [x] 1.3 Extract shared search utility from `web_search.py` into `app/domains/ai/research.py` — reusable `execute_search(query, max_results)` function for pipeline use (not a LangChain tool)
- [x] 1.4 Add `AI_MAX_RESEARCH_QUERIES` and `AI_MAX_FETCH_URLS` settings to `core/config.py`
- [x] 1.5 Write unit tests for URL fetcher (mock httpx) and search utility (mock Tavily)

## 2. Research Node
- [x] 2.1 Create Pydantic schemas in `schemas.py`: `ResearchQueriesOutput` (LLM generates queries), `ResearchContext` (compiled results)
- [x] 2.2 Create `app/domains/ai/prompts/research.py` — system prompt for research query generation with CoT reasoning
- [x] 2.3 Create `app/domains/ai/nodes/research.py` — research node that: generates queries via LLM, executes searches in parallel, fetches top URLs, compiles structured research context
- [x] 2.4 Add `format_research_context()` utility in `prompts/research.py` to format research results into a prompt-injectable block
- [x] 2.5 Write unit tests for research node with mocked search/fetch

## 3. Pipeline Integration — Research into Generation
- [x] 3.1 Update `service.py` `generate_board_stream()` to run research node before skeleton generation
- [x] 3.2 Yield new SSE events: `research_started`, `research_progress` (per query), `research_complete`
- [x] 3.3 Pass research context to skeleton generation, enrichment, and action generation prompts
- [x] 3.4 Add lightweight pre-research (1-2 queries) to question generation flow in `service.classify_and_generate_questions()`
- [x] 3.5 Add optional per-task research queries during enrichment (within budget)
- [x] 3.6 Write integration tests for research-augmented generation flow (mock LLM + search)

## 4. Skeleton Revision Step
- [x] 4.1 Create Pydantic schema `SkeletonReviewOutput` with `critique`, `has_issues`, and optional `revised_skeleton` fields
- [x] 4.2 Create `app/domains/ai/prompts/review_skeleton.py` — review prompt that critiques skeleton against research context
- [x] 4.3 Add `review_skeleton()` function in `nodes/generate_board.py` that calls the review LLM and optionally revises
- [x] 4.4 Integrate review step into `generate_board_stream()` — runs after initial skeleton, before enrichment
- [x] 4.5 Write tests for skeleton review (mock LLM, verify revision applies correctly)

## 5. Prompt Improvements — Chain-of-Thought and Few-Shot
- [x] 5.1 Add `reasoning` field to `ClassificationOutput`, `QuestionsOutput`, `BoardSkeletonOutput`, and `TaskEnrichmentOutput` schemas
- [x] 5.2 Update `prompts/classify.py` with CoT instructions and 1-2 few-shot examples
- [x] 5.3 Update `prompts/questions.py` with CoT instructions and 1-2 few-shot examples
- [x] 5.4 Update `prompts/generate_board.py` with CoT instructions and 1 few-shot example (skeleton structure)
- [x] 5.5 Update `prompts/enrich_task.py` with CoT instructions and 1 few-shot example
- [x] 5.6 Add research context injection points to all prompts that receive it

## 6. Graceful Degradation
- [x] 6.1 Ensure all research steps are skipped when `TAVILY_API_KEY` is not configured — generation proceeds as before
- [x] 6.2 Handle individual search/fetch failures without failing the pipeline (log and continue with available results)
- [x] 6.3 Handle research timeout — if total research time exceeds a threshold, proceed with partial results
- [x] 6.4 Write tests confirming generation works identically when Tavily is not configured

## 7. Frontend — Research Progress UI
- [x] 7.1 Update `useBoardGenerationStream` hook to handle new SSE events: `research_started`, `research_progress`, `research_complete`
- [x] 7.2 Add new phase states to the hook: "researching" between "connecting" and "skeleton"
- [x] 7.3 Update `BoardGenerationProgress` component to display research phase (e.g., "Researching visa requirements...", "Found 5 relevant sources...")
- [x] 7.4 Update generation phase text indicator for the new research phase
- [x] 7.5 Update Orval types if any API response schemas change

## 8. Configuration & Documentation
- [x] 8.1 Add new env vars to `.env.example` and Docker Compose config
- [x] 8.2 Update `_docs/` if applicable with new pipeline architecture
