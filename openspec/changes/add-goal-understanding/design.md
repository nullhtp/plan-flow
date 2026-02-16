## Context

This is the first AI-powered feature in PlanFlow (M2). It introduces two new backend domains (`goals`, `ai`), a new frontend feature module (`goals`), LangChain/LangGraph integration, and OpenRouter as the LLM provider. The change spans backend models, AI pipeline orchestration, API endpoints, and a frontend dynamic form renderer.

Solo developer, full-time. The `auth` domain and frontend auth feature are the only existing implementations to build on.

## Goals / Non-Goals

### Goals
- Users can enter a goal in natural language and receive AI-generated adaptive questions
- AI classifies goals by domain, complexity, and confidence — rejecting vague goals with helpful suggestions
- Dynamic form supports text, select, multiselect, and number field types
- Conditional follow-up: after initial answers, AI may generate 1 additional batch of follow-up questions
- Structured output enforcement: all LLM outputs validated against JSON schemas with retry
- Goal state machine tracks pipeline progress (`input` through `answered`)

### Non-Goals
- Board generation (M3)
- Goal listing / dashboard (M5)
- AI-assisted execution / task chat (M6)
- Cross-goal intelligence (M7)
- Streaming / SSE for AI responses (can add later if latency is a problem)
- OAuth or social login

## Decisions

### LLM Integration: LangChain + OpenRouter

**Decision:** Use LangChain's `ChatOpenAI` with OpenRouter's base URL (`https://openrouter.ai/api/v1`) for all LLM calls. Model configured via environment variable, defaulting to `openai/gpt-5.2`.

**Why:** LangChain provides structured output support (`.with_structured_output()`), retry logic, and model abstraction. OpenRouter allows switching models without code changes. This matches the project's planned architecture.

**Alternatives considered:**
- Direct OpenRouter HTTP calls — simpler but loses structured output parsing, retry helpers, and future LangGraph integration.
- LiteLLM — similar to LangChain's OpenAI wrapper but less ecosystem support for LangGraph.

### Pipeline: LangGraph State Graph

**Decision:** Define the classify → generate_questions flow as a LangGraph `StateGraph` with two nodes. The graph takes raw goal text as input and outputs either a rejection or a set of questions. Follow-up question generation reuses the `generate_questions` node with additional context (previous answers).

**Why:** LangGraph provides a clean state machine abstraction that will naturally extend to board generation (M3) and execution support (M6) by adding nodes. Starting with LangGraph now avoids a future rewrite.

**State shape:**
```python
class GoalPipelineState(TypedDict):
    raw_input: str
    classification: ClassificationOutput | None
    questions: list[QuestionSchema] | None
    answers: dict[str, Any] | None
    follow_up_questions: list[QuestionSchema] | None
    is_rejected: bool
    rejection_reason: str | None
    refinement_suggestions: list[str] | None
```

### Structured Output: Pydantic Models as JSON Schemas

**Decision:** Define Pydantic models for classification output and question schemas. Use LangChain's `.with_structured_output(PydanticModel)` to enforce JSON schema compliance. On validation failure, retry the same prompt up to 3 times before raising an error.

**Why:** Pydantic models are already the project standard (FastAPI, SQLModel). LangChain's structured output integration handles the JSON schema extraction and response parsing automatically.

### Confidence-Based Goal Rejection

**Decision:** The classification node outputs a `confidence` score (0.0-1.0). Goals below a configurable threshold (default: 0.3) are rejected with an AI-generated explanation and 2-3 refinement suggestions. The rejection response is part of the classification output, not a separate LLM call.

**Why:** A numeric confidence score is more flexible than a boolean flag — the threshold can be tuned without changing the prompt. The classification prompt already has enough context to generate refinement suggestions in the same call, saving an additional LLM round-trip.

### Goal Status State Machine

**Decision:** Goal.status is a string enum with ordered pipeline states:

```
input → classifying → questioning → answered → generating → active → completed → archived
```

M2 uses states through `answered`. Later milestones add transitions for `generating` (M3), `active`/`completed`/`archived` (M5).

**Why:** A single status field that tracks the full lifecycle lets the frontend route to the correct UI based on goal state. More granular than a simple draft/active/done model but avoids a separate "pipeline_stage" field.

### Adaptive Follow-ups: Max 1 Round

**Decision:** After the user submits initial answers, `POST /goals/:id/answers` calls the question generation node with the answers as additional context. The AI decides whether follow-ups are needed (it may return an empty list). Maximum 1 follow-up round — the second answer submission always completes questioning.

**Why:** Balances adaptiveness with UX predictability. Users always know they're at most 2 form submissions away from completion. The AI prompt instructs the model to only generate follow-ups when critical information is still missing.

**Implementation:** The `round` field on the answer submission request tracks which round it is. Round 1 may produce follow-ups. Round 2 always completes.

### API Design: Synchronous Single-Call

**Decision:** `POST /goals` creates the goal record AND runs the full classification + question generation pipeline, returning the result synchronously. No polling, no SSE.

**Why:** The combined classification + question generation should complete in 2-5 seconds with a fast model. This is within acceptable HTTP response time. Async/streaming adds significant complexity for minimal benefit at this stage. If latency becomes a problem, we can add SSE later without changing the API contract (just add an `Accept: text/event-stream` option).

**Timeout:** FastAPI route has a 30-second timeout. LLM calls individually timeout at 20 seconds.

### Frontend Form: Growing Pattern

**Decision:** The dynamic form renders all questions in a single scrollable view. When follow-up questions arrive after the first submission, they appear below the already-answered questions (which become read-only). Users can click "Edit" to modify previous answers, which resets the follow-up state.

**Why:** Growing form keeps all context visible. Users don't lose sight of what they've already answered. Simpler to implement than a wizard with back navigation.

### Data Storage: ai_context JSON Field

**Decision:** The Goal model's `ai_context` (JSON column) stores:
```json
{
  "classification": { "domain": "...", "complexity": 3, "confidence": 0.85, ... },
  "questions": [{ "id": "q1", "text": "...", "type": "select", ... }],
  "answers": { "q1": "value", "q2": ["opt1", "opt2"], ... },
  "follow_up_questions": [{ "id": "fq1", ... }],
  "follow_up_answers": { "fq1": "value", ... }
}
```

No separate Conversation model for M2 — the questioning exchange is simple enough to fit in `ai_context`. The Conversation model will be introduced in M6 for execution-phase chat.

**Why:** Keeps the data model simple. One JSON field captures everything needed for board generation (M3). No extra tables, no join queries. The field is already planned in PROJECT.md.

## Risks / Trade-offs

- **LLM latency** — synchronous API calls mean the user waits 2-5 seconds per submission. Mitigation: good loading UI, timeouts, error recovery. Can add streaming later.
- **LLM output quality** — question quality depends heavily on prompt engineering. Mitigation: structured output enforcement, 3x retry, test with diverse goal types.
- **OpenRouter availability** — single provider dependency. Mitigation: LangChain abstraction allows swapping to direct provider calls. Graceful error messaging on failure.
- **ai_context growth** — JSON field could grow large with many questions/answers. Mitigation: 3-7 questions per round, max 2 rounds = 14 questions max. Well within JSON column limits.
- **Model cost** — GPT-5.2 is not the cheapest model. Mitigation: classification + questions are relatively short prompts. Monitor cost per goal creation. Can switch to cheaper model for classification later.

## Open Questions

- Exact confidence threshold for rejection (0.3 default — may need tuning after testing with real goals)
- Whether to add rate limiting on goal creation in M2 or defer to M8 (Polish)
