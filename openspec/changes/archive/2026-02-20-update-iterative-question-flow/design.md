## Context
The current pregeneration flow has a fixed 2-round question cycle: 3-7 initial questions, then optionally 1 follow-up round (decided by AI). This limits the AI's ability to gather comprehensive context for complex goals. The change introduces unlimited iterative questioning with progressive deepening, a readiness score, and a streamlined UI that merges the question and summary steps.

Key stakeholders: end users creating goals, AI pipeline, backend API, frontend wizard.

## Goals / Non-Goals

**Goals:**
- Allow unlimited question-answer iterations before board generation
- AI progressively deepens questions based on accumulated context
- Show a readiness indicator so users know board quality at any point
- Keep the "Generate Board" button always accessible after round 1
- Maintain backward compatibility with existing goals in the database

**Non-Goals:**
- Changing the board generation pipeline itself (skeleton, enrichment)
- Modifying the sub-board question flow (it remains fixed 1-round)
- Real-time streaming of questions (questions are still generated synchronously per round)
- Changing the initial goal classification flow

## Decisions

### 1. Round data structure in ai_context
**Decision:** Store rounds as an ordered array `rounds: [{ round: number, questions: [...], answers: {...}, readiness: {...} }]` in `ai_context`, replacing the current flat `questions`/`answers`/`follow_up_questions`/`follow_up_answers` structure.

**Alternatives considered:**
- Keep flat structure with numbered keys (e.g., `questions_3`, `answers_3`) — messy, hard to iterate
- Store in separate database table — over-engineered for JSON context data

**Migration:** Existing goals with old `ai_context` format continue to work. The backend reads the old format and converts on-the-fly when needed. New goals use the new format from round 1.

### 2. Readiness score computation
**Decision:** The AI returns a `ReadinessAssessment` alongside each question batch, containing: `score` (float 0.0-1.0), `covered_dimensions` (list of strings), `uncovered_dimensions` (list of strings), and `summary` (short text description of readiness). This is part of the structured output from the question generation LLM call — no separate API call needed.

**Alternatives considered:**
- Separate LLM call for readiness — adds latency and cost
- Heuristic-based score (count answered vs. total dimensions) — less accurate, doesn't account for answer quality

### 3. Progressive deepening prompt strategy
**Decision:** The question generation prompt receives the full Q&A history and explicit instructions to: (a) not repeat topics already covered, (b) drill deeper into partially covered dimensions, (c) explore new dimensions if all current ones are sufficiently covered, (d) ask fewer questions per round (2-4) to keep the flow lightweight.

**Alternatives considered:**
- Separate "depth planner" node that decides topics before question generation — over-engineered
- Fixed topic rotation — not adaptive to user's specific situation

### 4. UI pattern: growing form with sticky Generate
**Decision:** The form grows downward. Each submitted round becomes a read-only collapsible section with an "Edit" button. New questions appear below. A sticky footer bar contains the readiness indicator and "Generate Board" button. The separate summary step (`GoalSummary` component) is removed.

**Alternatives considered:**
- Chat-like UI — inconsistent with the existing question/answer chip-based UX
- Wizard with pagination — loses context of previous answers

### 5. Edit and re-generate behavior
**Decision:** When the user clicks "Edit" on round N, rounds N+1 and beyond are discarded from both UI state and backend (`ai_context`). On re-submitting the edited round, the AI generates fresh follow-up questions from that point. The backend exposes a `DELETE /api/goals/:id/rounds/:round` endpoint to truncate rounds, or the `POST /api/goals/:id/answers` endpoint handles truncation when `round` is less than the current max round.

**Alternatives considered:**
- Optimistic truncation (frontend only, sync on next submit) — simpler but risks inconsistency
- No editing — poor UX

**Decision:** Use the answer submission endpoint to handle truncation implicitly. When the backend receives answers for round N and rounds > N exist in `ai_context`, it truncates everything after round N before storing the new answers. No separate delete endpoint needed.

### 6. Goal status during iterative questioning
**Decision:** The goal remains in `questioning` status throughout all rounds. The `answered` status is only set when the user triggers board generation (at which point it transitions `questioning` -> `answered` -> `generating` in quick succession). This simplifies the state machine — the user is always "questioning" until they choose to generate.

**Alternatives considered:**
- New `ready` status between `questioning` and `generating` — unnecessary intermediate state
- Keep transitioning to `answered` after each round — confusing since the user may not be "done" answering

## Risks / Trade-offs
- **Increased LLM costs**: More question rounds = more LLM calls. Mitigated by keeping rounds small (2-4 questions) and the readiness score encouraging users to generate when coverage is sufficient.
- **Answer fatigue**: Users might get tired of answering questions. Mitigated by progressive deepening (questions become more relevant) and the always-visible Generate button.
- **Backward compatibility**: Existing goals with old `ai_context` format need migration handling. Mitigated by on-the-fly conversion in the backend read path.
- **Prompt size growth**: Full Q&A history gets large after many rounds. Mitigated by summarizing earlier rounds in the prompt when history exceeds a threshold (e.g., > 5 rounds).

## Open Questions
- Should there be a maximum round limit (e.g., 20) to prevent abuse? Likely yes, as a safety valve, but set high enough that no user would reasonably hit it.
