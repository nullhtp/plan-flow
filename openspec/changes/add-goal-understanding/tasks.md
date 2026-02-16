## 1. Backend — Goal Domain Foundation

- [ ] 1.1 Create `backend/app/domains/goals/` package with `__init__.py`
- [ ] 1.2 Define Goal SQLModel in `goals/models.py` (id, user_id, title, original_input, status enum, ai_context JSON, created_at, updated_at)
- [ ] 1.3 Create Alembic migration for `goal` table with FK to `user` and index on `user_id`
- [ ] 1.4 Run migration against dev database and verify table structure
- [ ] 1.5 Define Pydantic schemas in `goals/schemas.py`: `GoalCreate`, `GoalResponse`, `GoalQuestionsResponse`, `GoalRejectionResponse`, `AnswerSubmission`, `AnswerResponse`

## 2. Backend — AI Domain Foundation

- [ ] 2.1 Add AI dependencies to `pyproject.toml`: `langchain`, `langchain-openai`, `langgraph`
- [ ] 2.2 Add OpenRouter config to `core/config.py`: `OPENROUTER_API_KEY`, `AI_DEFAULT_MODEL` (default `openai/gpt-5.2`), `AI_CONFIDENCE_THRESHOLD` (default 0.3), `AI_LLM_TIMEOUT` (default 20s), `AI_MAX_RETRIES` (default 3)
- [ ] 2.3 Create `backend/app/domains/ai/` package with `__init__.py`
- [ ] 2.4 Define AI output Pydantic models in `ai/schemas.py`: `ClassificationOutput`, `QuestionSchema`, `QuestionsOutput`, `FollowUpInput`

## 3. Backend — AI Pipeline Implementation

- [ ] 3.1 Write classification system prompt in `ai/prompts/classify.py`
- [ ] 3.2 Write question generation system prompt in `ai/prompts/questions.py`
- [ ] 3.3 Implement classification node in `ai/nodes/classify.py` using LangChain `ChatOpenAI` with `.with_structured_output(ClassificationOutput)`
- [ ] 3.4 Implement question generation node in `ai/nodes/questions.py` using `.with_structured_output(QuestionsOutput)`
- [ ] 3.5 Define `GoalPipelineState` TypedDict and LangGraph `StateGraph` in `ai/pipeline.py` with classify → generate_questions flow and rejection short-circuit
- [ ] 3.6 Implement retry wrapper (up to 3 retries on Pydantic validation failure) as a utility in `ai/service.py` or decorator
- [ ] 3.7 Implement AI service functions in `ai/service.py`: `classify_and_generate_questions(raw_input)`, `generate_follow_up_questions(classification, questions, answers)`
- [ ] 3.8 Manual smoke test: call `classify_and_generate_questions` with 3-5 diverse goal strings and verify output structure

## 4. Backend — Goals API Endpoints

- [ ] 4.1 Implement `goals/service.py`: `create_goal(user_id, original_input)` — creates Goal record, calls AI service, updates ai_context and status, handles rejection
- [ ] 4.2 Implement `goals/service.py`: `submit_answers(goal_id, user_id, answers, round)` — validates goal ownership/status, stores answers, optionally triggers follow-up generation, updates status
- [ ] 4.3 Implement `goals/service.py`: `get_goal(goal_id, user_id)` — retrieves goal with ownership check
- [ ] 4.4 Implement `goals/router.py`: `POST /api/goals` — calls create_goal, returns 201 with questions or 422 with rejection
- [ ] 4.5 Implement `goals/router.py`: `POST /api/goals/{goal_id}/answers` — calls submit_answers, returns follow-ups or completion
- [ ] 4.6 Implement `goals/router.py`: `GET /api/goals/{goal_id}` — calls get_goal, returns goal data
- [ ] 4.7 Register goals router in `main.py` under `/api` prefix
- [ ] 4.8 Regenerate OpenAPI spec and verify new endpoints appear

## 5. Backend — Testing

- [ ] 5.1 Create test fixtures in `tests/conftest.py`: sample goal data, mock AI service responses
- [ ] 5.2 Write unit tests for Goal model creation and status transitions
- [ ] 5.3 Write integration tests for `POST /api/goals` — success case (mocked AI), rejection case, unauthenticated case
- [ ] 5.4 Write integration tests for `POST /api/goals/:id/answers` — round 1 with follow-ups, round 1 without follow-ups, round 2 completion, wrong status, wrong owner
- [ ] 5.5 Write integration tests for `GET /api/goals/:id` — success, not found, wrong owner
- [ ] 5.6 Write AI output schema validation tests: verify ClassificationOutput and QuestionsOutput against sample LLM responses
- [ ] 5.7 Write retry logic test: mock malformed LLM output, verify retries, verify error after exhaustion
- [ ] 5.8 Run full backend test suite, fix any failures

## 6. Frontend — API Client Generation

- [ ] 6.1 Run Orval codegen to generate TypeScript types and React Query hooks for new goal endpoints
- [ ] 6.2 Verify generated types match backend schemas (GoalResponse, QuestionSchema, etc.)

## 7. Frontend — Goal Input Page

- [ ] 7.1 Create `features/goals/` directory structure: `components/`, `hooks/`, `types.ts`
- [ ] 7.2 Implement `GoalInput` component: text input, submit button, example goal suggestions
- [ ] 7.3 Implement goal creation hook using generated React Query mutation
- [ ] 7.4 Implement loading state component for AI processing
- [ ] 7.5 Implement `VagueGoalRejection` component: rejection message, clickable refinement suggestions
- [ ] 7.6 Add route `/goals/new` with auth protection

## 8. Frontend — Dynamic Question Form

- [ ] 8.1 Implement `DynamicQuestionForm` component: renders questions based on field type
- [ ] 8.2 Implement individual field renderers: `TextField`, `SelectField`, `MultiselectField`, `NumberField`
- [ ] 8.3 Implement per-question rationale display as helper text
- [ ] 8.4 Implement required field validation and submit button disable logic
- [ ] 8.5 Implement answer submission hook using generated React Query mutation
- [ ] 8.6 Implement growing form pattern: read-only initial answers + follow-up questions below
- [ ] 8.7 Implement "Edit" button to reset initial answers and remove follow-ups

## 9. Frontend — Post-Answer Summary and Navigation

- [ ] 9.1 Implement `GoalSummary` component: displays goal title, original input, all Q&A pairs
- [ ] 9.2 Add disabled "Generate Board" button with "coming soon" tooltip
- [ ] 9.3 Add route `/goals/:id` that renders appropriate view based on goal status
- [ ] 9.4 Implement AI error display component with "Try Again" retry button
- [ ] 9.5 Add navigation from home page (`/`) to `/goals/new`
- [ ] 9.6 Run Orval codegen one final time to ensure all types are current

## 10. Frontend — Testing

- [ ] 10.1 Write component tests for `GoalInput`: renders input, example clicks populate field, submit triggers mutation
- [ ] 10.2 Write component tests for `DynamicQuestionForm`: renders all field types, validation, submit
- [ ] 10.3 Write component tests for growing form: follow-ups appear, edit resets state
- [ ] 10.4 Write component tests for `VagueGoalRejection`: displays suggestions, click populates input
- [ ] 10.5 Write component tests for `GoalSummary`: displays Q&A, generate button disabled
- [ ] 10.6 Run full frontend test suite, fix any failures

## 11. End-to-End Validation

- [ ] 11.1 Manual E2E test: create goal → receive questions → submit answers → see follow-ups → submit follow-ups → see summary
- [ ] 11.2 Manual E2E test: submit vague goal → see rejection → click suggestion → resubmit → receive questions
- [ ] 11.3 Manual E2E test: AI timeout/error → see error message → retry → success
- [ ] 11.4 Test with diverse goal types: personal (move), professional (launch product), creative (write novel), learning (learn language), health (train for marathon), logistical (plan wedding)
- [ ] 11.5 Verify Docker Compose works with new AI dependencies and env vars
- [ ] 11.6 Verify CI pipeline passes with new code (linting, type checking, tests)

**Parallelizable work:**
- Tasks 1.x and 2.x can run in parallel (Goals domain foundation and AI domain foundation)
- Tasks 7.x and 8.x can start once 6.x is done (frontend components are independent of each other)
- Task 10.x (frontend tests) can be written alongside 7.x-9.x

**Dependencies:**
- 3.x depends on 2.x (AI pipeline needs AI foundation)
- 4.x depends on 1.x and 3.x (Goals API needs Goal model and AI service)
- 5.x depends on 4.x (backend tests need endpoints)
- 6.x depends on 4.8 (codegen needs OpenAPI spec from registered endpoints)
- 7.x-9.x depend on 6.x (frontend needs generated types/hooks)
- 11.x depends on all previous sections
