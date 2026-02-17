# Change: Add board meta context for AI-powered generation

## Why
The AI board and question generation currently operates without environmental context about the user — no timezone, location, current date, locale, or device type. This limits the AI's ability to generate contextually relevant tasks (e.g., realistic due dates relative to today, location-aware suggestions, locale-appropriate formatting). Adding automatic meta collection gives the AI richer context for both question generation and board generation, producing more personalized and actionable plans.

## What Changes
- **Goal ai_context**: Add a `user_meta` key inside `Goal.ai_context` at goal creation time, storing timezone, locale, current datetime, location, and device type. This is the single source of truth for meta — both question generation and board generation read from here.
- **Frontend meta collection**: Collect user meta (timezone, locale, device type) from the browser at goal creation. Request browser Geolocation API permission on the goal creation page; fall back to passing the client IP for server-side resolution.
- **AI prompts**: Inject meta context into question generation, follow-up question generation, board skeleton generation, and task enrichment prompts.
- **Frontend board detail**: Display meta context on the board detail page (e.g., location, generation date), read from the goal's `ai_context.user_meta` via the board's related goal.
- **API schema changes**: Accept optional `user_meta` in the goal creation request body. Include `user_meta` in `BoardResponse` (computed from the related goal, no new DB column).

## Impact
- Affected specs: `board-management`, `goal-management`, `ai-pipeline`
- Affected code:
  - `backend/app/domains/goals/schemas.py` — GoalCreate (accept user_meta)
  - `backend/app/domains/goals/service.py` — store user_meta in ai_context
  - `backend/app/domains/goals/router.py` — pass client IP for geolocation fallback
  - `backend/app/domains/boards/schemas.py` — BoardResponse (include user_meta from goal)
  - `backend/app/domains/boards/service.py` — read user_meta from goal.ai_context for board response
  - `backend/app/domains/boards/router.py` — pass user_meta to AI generation pipeline
  - `backend/app/domains/ai/prompts/` — all prompt modules (inject meta)
  - `backend/app/domains/ai/service.py` — pass meta through generation pipeline
  - `frontend/src/features/goals/components/` — collect and send meta
  - `frontend/src/features/board/components/` — display meta on board detail
