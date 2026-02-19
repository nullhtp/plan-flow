# Change: Add universal user context to all AI generations

## Why
Currently, user context (date, timezone, locale, location, device type) is only injected into the board generation pipeline prompts. Chat endpoints (task chat, board chat), classification, and subtask action generation receive no temporal or environmental context. This means the AI cannot reason about time-sensitivity, scheduling, or locale-appropriate formatting during chat or classification.

## What Changes
- Inject a standardized "User context" block into **every** LLM call site: classification, question generation, board skeleton, task enrichment, task chat, board chat, subtask action suggestions, and sub-board questions
- Add day-of-week to the user context block alongside the existing date field
- For chat endpoints: derive context server-side from the goal's stored `user_meta` (timezone, locale, location, device) and compute the current date from the server clock + stored timezone — no API schema changes needed
- For classification: pass `user_context` as a new parameter so the LLM can factor in temporal context when classifying goals
- Extend `format_user_meta_block()` to include day-of-week

## Impact
- Affected specs: `ai-pipeline`, `ai-memory`
- Affected code:
  - `backend/app/domains/ai/prompts/meta.py` — add day-of-week
  - `backend/app/domains/ai/prompts/chat.py` — add `{user_context}` placeholder
  - `backend/app/domains/ai/prompts/board_chat.py` — add `{user_context}` placeholder
  - `backend/app/domains/ai/prompts/action_suggestions.py` — add context injection
  - `backend/app/domains/ai/graphs/chat.py` — add `user_context` to state schema
  - `backend/app/domains/ai/graphs/board_chat.py` — add `user_context` to state schema
  - `backend/app/domains/ai/router.py` — resolve user_meta from goal for chat endpoints, compute current date server-side
  - `backend/app/domains/ai/nodes/classify.py` — accept and use `user_context`
  - `backend/app/domains/ai/service.py` — pass `user_context` through classification calls
