# Change: Add Goal Understanding Pipeline (M2)

## Why

PlanFlow's core value proposition starts with turning a user's goal into a structured plan. The first half of this pipeline — goal classification and adaptive question generation — is the critical first touch: the user types a goal, the AI understands it, and presents a tailored dynamic form to gather the specifics needed for board generation. Without this, the product is an empty kanban tool with no AI differentiation.

This is **M2** on the roadmap — the first milestone after Auth (M1) that introduces AI capabilities.

## What Changes

### Backend — New `goals` Domain
- Goal SQLModel with pipeline-aware status tracking (`input` → `classifying` → `questioning` → `answered` → `generating` → `active` → `completed` → `archived`)
- `POST /goals` — creates goal from raw text, runs classification + question generation in one call; returns questions or rejection
- `POST /goals/:id/answers` — submit answers; returns follow-up questions (if any) or confirmation that questioning is complete
- `GET /goals/:id` — retrieve goal with current status and questions/answers

### Backend — New `ai` Domain (Foundation)
- OpenRouter client integration via LangChain (`ChatOpenAI` with OpenRouter base URL)
- LangGraph pipeline with two nodes: **classify** and **generate_questions**
- **Goal classification node** — determines domain, complexity (1-5), confidence score (0-1), key dimensions, and generates a clean suggested title. Goals below a confidence threshold are rejected with AI-generated refinement suggestions.
- **Question generation node** — produces 3-7 structured questions with field types (text, select, multiselect, number), options, and per-question rationale explaining why the question matters
- **Adaptive follow-up** — after initial answers, the AI may generate up to 1 additional batch of follow-up questions based on the answers
- Structured output enforcement with JSON schema validation and up to 3 automatic retries on malformed LLM output
- System prompts stored as separate modules in `prompts/`

### Frontend — New `goals` Feature Module
- "New Goal" page with free-text input and example goal suggestions for inspiration
- Dynamic form renderer that handles text, select, multiselect, and number field types
- Growing form UX — follow-up questions appear below already-answered questions
- Per-question rationale displayed as helper text
- Loading states during AI processing
- Error handling for AI failures, vague goal rejection with refinement suggestions
- Post-answer summary page showing goal + answers with a "Generate Board" button (disabled placeholder until M3)

### Database
- Goal model + Alembic migration
- `ai_context` JSON field stores classification output, questions, and answers

## Impact
- Affected specs: none (all new capabilities)
- New specs: `goal-management`, `ai-pipeline`, `goal-input-ui`
- Affected code:
  - New: `backend/app/domains/goals/` (models, schemas, router, service)
  - New: `backend/app/domains/ai/` (schemas, service, pipeline, nodes, prompts)
  - New: `frontend/src/features/goals/` (components, hooks)
  - New: `frontend/src/routes/` (goal-related routes)
  - Modified: `backend/app/main.py` (register new routers)
  - Modified: `frontend/src/routes/router.ts` (add goal routes)
  - New: `backend/app/core/config.py` (OpenRouter API key, model settings)
  - New: Alembic migration for Goal table
