## 1. Backend: AI Pipeline — Readiness Schema & Iterative Question Prompt
- [ ] 1.1 Add `ReadinessAssessment` Pydantic schema to `app/domains/ai/schemas.py` (`score: float`, `covered_dimensions: list[str]`, `uncovered_dimensions: list[str]`, `summary: str`)
- [ ] 1.2 Extend `QuestionsOutput` schema to include a `readiness: ReadinessAssessment` field alongside `questions`
- [ ] 1.3 Update `app/domains/ai/prompts/questions.py` — refactor `QUESTIONS_SYSTEM_PROMPT` to accept round number, full Q&A history, and dimension coverage; instruct AI to produce readiness assessment; generate 2-4 questions for follow-up rounds (3-7 for round 1); avoid repeating covered topics
- [ ] 1.4 Update `FOLLOW_UP_SYSTEM_PROMPT` — merge into the main prompt (the distinction between initial and follow-up is now just the round number and presence of Q&A history)
- [ ] 1.5 Add Q&A history summarization utility for prompts with >5 rounds (summarize early rounds, keep recent ones in full)

## 2. Backend: AI Service — Iterative Question Generation
- [ ] 2.1 Update `generate_follow_up_questions()` in `app/domains/ai/service.py` to accept full rounds history and round number; return `QuestionsOutput` (questions + readiness) instead of just questions
- [ ] 2.2 Update `classify_and_generate_questions()` to return `QuestionsOutput` with initial readiness assessment (score ~0.0, all dimensions uncovered)
- [ ] 2.3 Update question generation node (`app/domains/ai/nodes/questions.py`) to pass round number and full Q&A history to the prompt

## 3. Backend: Goal Service — Rounds-Based ai_context
- [ ] 3.1 Update `process_goal_creation()` in `app/domains/goals/service.py` to store round 1 questions in new `ai_context.rounds` format: `[{ round: 1, questions: [...], answers: {}, readiness: {...} }]`
- [ ] 3.2 Update `process_answers()` to: store answers in `ai_context.rounds[round-1].answers`, truncate later rounds if round < max, call `generate_follow_up_questions()` with full round history, append new round entry with generated questions
- [ ] 3.3 Remove the `is_complete` logic and `answered` status transition from `process_answers()` — goal stays in `questioning`
- [ ] 3.4 Add backward compatibility reader: function to detect old flat `ai_context` format and convert to rounds array on-the-fly
- [ ] 3.5 Rename `revert_goal_to_answered()` to `revert_goal_to_questioning()` — revert to `questioning` instead of `answered`
- [ ] 3.6 Update all callers of `revert_goal_to_answered()` across boards domain to use `revert_goal_to_questioning()`

## 4. Backend: Goal & Board API — Response Schema Changes
- [ ] 4.1 Update `GoalAnswersResponse` schema in `app/domains/goals/schemas.py` — replace `is_complete`/`follow_up_questions` with `next_questions`, `readiness`, `next_round`
- [ ] 4.2 Update `GoalQuestionsResponse` to include `readiness` field
- [ ] 4.3 Update goal answers router handler to return new response format
- [ ] 4.4 Update board generation endpoint to accept goals in `questioning` status (in addition to `answered` for backward compat)
- [ ] 4.5 Update `_format_qa_context()` in `app/domains/boards/board_service.py` to read from rounds-based `ai_context` format (with backward compat for old format)
- [ ] 4.6 Regenerate Orval API types after OpenAPI spec changes

## 5. Frontend: Growing Question Form
- [ ] 5.1 Refactor `DynamicQuestionForm` component to support unlimited rounds — accept `rounds: Round[]` prop instead of separate initial/followUp props
- [ ] 5.2 Add collapsible read-only round sections for completed rounds (collapsed by default, expandable)
- [ ] 5.3 Add "Edit" button per round that triggers truncation (discard later rounds) and makes that round editable
- [ ] 5.4 Add auto-scroll to new questions after round submission
- [ ] 5.5 Add loading indicator below submitted answers while AI generates next questions

## 6. Frontend: Sticky Generate Footer & Readiness Indicator
- [ ] 6.1 Create `ReadinessIndicator` component — circular progress ring with percentage, covered/uncovered dimension tags, color-coded (red <0.4, yellow 0.4-0.7, green 0.7+), readiness summary text
- [ ] 6.2 Create `GenerateFooter` component — sticky footer bar with `ReadinessIndicator` and "Generate Board" button
- [ ] 6.3 Integrate footer into `goals.new.tsx` — show after round 1 is answered, persist across all rounds

## 7. Frontend: Page State Machine Update
- [ ] 7.1 Update `goals.new.tsx` `PageState` type — remove `summary` step, add rounds tracking to `questions` step, add readiness state
- [ ] 7.2 Update `handleSubmitAnswers` to: append new round from API response, update readiness state, transition to show new questions (no `answered`/`summary` step)
- [ ] 7.3 Update edit handler to truncate rounds and re-submit
- [ ] 7.4 Remove `GoalSummary` usage from the goal creation wizard (keep component file for potential other uses)
- [ ] 7.5 Update `goals.$goalId.tsx` to display growing form with rounds when goal is in `questioning` status

## 8. Testing & Validation
- [ ] 8.1 Update backend tests for answer submission — test multi-round flow (rounds 1-5), truncation on edit, readiness in response
- [ ] 8.2 Update backend tests for goal creation — verify rounds format in ai_context, readiness in response
- [ ] 8.3 Test backward compatibility — existing goals with old flat ai_context format still work
- [ ] 8.4 Test board generation from `questioning` status
- [ ] 8.5 Run full build and fix any type errors (frontend + backend)
