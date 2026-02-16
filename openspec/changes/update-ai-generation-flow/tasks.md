## 1. Language Detection in Classification

- [ ] 1.1 Add `language: str` field to `ClassificationOutput` in `ai/schemas.py`
- [ ] 1.2 Update `prompts/classify.py` — add language detection instruction to system prompt (detect ISO 639-1 code from input)
- [ ] 1.3 Update `nodes/classify.py` — no changes needed (schema drives output)
- [ ] 1.4 Update `ai/service.py` `classify_and_generate_questions` — store `language` in returned result
- [ ] 1.5 Update `goals/service.py` or `boards/service.py` — ensure `language` is persisted in `goal.ai_context`
- [ ] 1.6 Add language instruction to `prompts/questions.py` — both initial and follow-up prompts include "Respond in {language}"
- [ ] 1.7 Write unit tests: classification with English, Russian, Spanish inputs returns correct `language` field

## 2. New Pydantic Schemas for Two-Step Generation

- [ ] 2.1 Create `BoardSkeletonTaskOutput` schema (id, title, depends_on, is_goal_node) in `ai/schemas.py`
- [ ] 2.2 Create `BoardSkeletonOutput` schema (board_title, tasks: list[BoardSkeletonTaskOutput]) in `ai/schemas.py`
- [ ] 2.3 Create `SubtaskOutput` schema (title) in `ai/schemas.py`
- [ ] 2.4 Create `TaskEnrichmentOutput` schema (description, due_date, priority, estimated_minutes, subtasks: list[SubtaskOutput]) in `ai/schemas.py`
- [ ] 2.5 Keep existing `BoardGenerationOutput` and `BoardGenerationTaskOutput` temporarily for backward compat during migration (remove after full switch)

## 3. Skeleton Generation Node and Prompt

- [ ] 3.1 Rewrite `prompts/generate_board.py` — skeleton-only prompt: generate task names + dependency graph + goal node flag, in detected language. Remove description/metadata/subtask instructions.
- [ ] 3.2 Update `nodes/generate_board.py` — new `generate_board_skeleton()` function returning `BoardSkeletonOutput`. Remove or rename old `generate_board()`.
- [ ] 3.3 Validate skeleton output with existing `dag_utils.validate_dag()` and `validate_goal_node()`
- [ ] 3.4 Write unit tests: skeleton node returns valid DAG with titles only, no descriptions

## 4. Task Enrichment Node and Prompt

- [ ] 4.1 Create `prompts/enrich_task.py` — enrichment prompt: given task title, graph context, goal context, and language, generate description + metadata + 2-5 subtasks in the target language
- [ ] 4.2 Create `nodes/enrich_task.py` — `enrich_task()` function returning `TaskEnrichmentOutput`
- [ ] 4.3 Write unit tests: enrichment node returns description, metadata, and subtasks for a given task

## 5. AI Service Orchestration (Streaming Generator)

- [ ] 5.1 Add `ai_enrichment_concurrency` setting to `core/config.py` (default: 5, from `AI_ENRICHMENT_CONCURRENCY` env var)
- [ ] 5.2 Implement `generate_board_stream()` async generator in `ai/service.py`:
  - Calls skeleton node with retry loop (up to `ai_max_retries`)
  - Yields `skeleton_ready` event
  - Runs enrichment calls in parallel via `asyncio.Semaphore` + `asyncio.create_task`
  - Yields `task_enriched` per completed enrichment (with per-task retry)
  - Yields `generation_complete` with `failed_tasks` list
  - Yields `generation_error` on unrecoverable skeleton failure
- [ ] 5.3 Define SSE event dataclasses/TypedDicts for type-safe event payloads
- [ ] 5.4 Write integration tests: mock LLM calls, verify event sequence (skeleton_ready → N x task_enriched → generation_complete)

## 6. Board Persistence — Two-Phase

- [ ] 6.1 Implement `create_board_from_skeleton()` in `boards/service.py` — create Board + Task (empty descriptions) + TaskDependency records, return AI-ID-to-UUID mapping
- [ ] 6.2 Implement `update_task_with_enrichment()` in `boards/service.py` — update single Task record with description/metadata, create Subtask records
- [ ] 6.3 Update `generate_board_for_goal()` to use the streaming flow: persist skeleton → stream enrichments → transition goal to active
- [ ] 6.4 Write unit tests: skeleton persistence creates correct records; enrichment updates individual tasks; rollback on skeleton failure

## 7. SSE Streaming Endpoint

- [ ] 7.1 Replace `POST /api/goals/:id/generate-board` in `boards/router.py` with SSE streaming using `StreamingResponse(media_type="text/event-stream")`
- [ ] 7.2 Implement SSE event formatting: `event: {type}\ndata: {json}\n\n`
- [ ] 7.3 Handle pre-flight validation (goal ownership, status, no existing board) before starting stream — return 409/404/401 as regular HTTP errors
- [ ] 7.4 Handle client disconnect gracefully (check if client is still connected before yielding events)
- [ ] 7.5 Write integration tests: test SSE event stream end-to-end with test client

## 8. Clean Up and Remove Old Code

- [ ] 8.1 Remove old `generate_board_from_context()` from `ai/service.py` (replaced by `generate_board_stream()`)
- [ ] 8.2 Remove old `BoardGenerationOutput` / `BoardGenerationTaskOutput` from `ai/schemas.py` if no longer referenced
- [ ] 8.3 Remove old monolithic prompt content from `prompts/generate_board.py`
- [ ] 8.4 Update `pipeline.py` LangGraph graph definition to reflect new skeleton + enrichment nodes

## 9. End-to-End Validation

- [ ] 9.1 Manual test: create goal in English → generate board → verify SSE events stream correctly with English content
- [ ] 9.2 Manual test: create goal in Russian → verify all generated content (titles, descriptions, subtasks) is in Russian
- [ ] 9.3 Manual test: verify concurrency limit works (check logs for parallel enrichment with default concurrency 5)
- [ ] 9.4 Run full test suite (`pytest`) — ensure all existing tests pass or are updated
