# Change: Update AI board generation to multi-step streaming flow with language matching

## Why
The current board generation pipeline makes a single monolithic LLM call that produces the entire board (structure, descriptions, metadata) at once. This is slow (~15-30s of dead silence for the user), produces lower-quality results because the LLM must handle too many concerns in one pass, and always responds in English regardless of the user's input language.

## What Changes
- **Language detection in classification**: Extend the classification node to detect the user's input language. All subsequent AI outputs (board title, task names, descriptions, subtasks) SHALL be generated in that detected language.
- **Two-step board generation**: Replace the single-call board generation with a two-step graph:
  1. **Skeleton step**: Generate the board structure — task names and the full dependency graph (DAG edges). This is a lightweight call producing only the scaffolding.
  2. **Enrichment step**: For each task in parallel, generate the full description, progressive metadata (due_date, priority, estimated_minutes), and subtasks. Uses configurable concurrency to manage API rate limits.
- **SSE streaming endpoint**: Replace the existing `POST /goals/:id/generate-board` endpoint with a streaming SSE endpoint. Events: `skeleton_ready` (board structure visible immediately), `task_enriched` (per-task as enrichment completes), `generation_complete`, `generation_error`.
- **Auto-generated subtasks**: Every task receives AI-generated subtasks during board generation (no longer on-demand only).

## Impact
- Affected specs: `ai-pipeline`, `board-management`
- Affected code:
  - `backend/app/domains/ai/schemas.py` — new skeleton + enrichment schemas
  - `backend/app/domains/ai/nodes/generate_board.py` — split into skeleton + enrichment nodes
  - `backend/app/domains/ai/prompts/generate_board.py` — split into skeleton + enrichment prompts
  - `backend/app/domains/ai/service.py` — new orchestration with parallel enrichment
  - `backend/app/domains/ai/nodes/classify.py` — add language detection to output
  - `backend/app/domains/ai/prompts/classify.py` — add language detection instruction
  - `backend/app/domains/boards/router.py` — SSE streaming endpoint replaces current POST
  - `backend/app/domains/boards/service.py` — streaming board generation orchestration
  - `backend/app/domains/boards/models.py` — no schema changes (subtasks already exist)
  - Frontend API client — consume SSE instead of POST (out of scope for this change, frontend delta not included)
