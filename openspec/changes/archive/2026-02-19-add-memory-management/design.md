## Context

The AI memory system stores facts about users automatically (preferences, past goals, patterns) but provides zero visibility or control. Users cannot see, edit, delete, or toggle memories. Chat responses give no indication of which memories influenced the AI. Memories persist forever with no cleanup.

This change spans backend (new domain, modified AI domain, new API endpoints), frontend (new settings feature, memory panel on boards, chat message badges), and the AI pipeline (memory IDs tracking through retrieval → prompt → response).

## Goals / Non-Goals

- Goals:
  - Full memory CRUD via REST API
  - Per-user memory toggle (DB-persisted, overrides global flag)
  - Settings page with memory list, search, edit, delete, bulk-clear, toggle
  - Contextual memory sidebar on board pages showing relevant memories
  - Memory badges on AI chat messages showing which memories were used
  - Memory decay: time-based archival of unused memories + hard cap per user
  - Re-embedding on edit for accurate future retrieval

- Non-Goals:
  - LLM-based memory extraction (keep rule-based)
  - Memory extraction from chat conversations (future work)
  - Memory sharing between users
  - Memory import/export
  - Memory categories management (categories remain system-defined)

## Decisions

### 1. New `settings` backend domain vs. extending `auth`
- **Decision**: Create a new `app/domains/settings/` domain for user settings
- **Why**: Settings will grow beyond memory (theme, notifications, etc.). Keeping it separate follows the domain-based architecture. The `user_settings` table stores per-user preferences as a single row with typed columns, not a key-value store.
- **Alternatives**: Key-value `user_preferences` table (more flexible but harder to type-check); adding fields directly to the `User` model (pollutes auth domain).

### 2. Soft-delete for memories via `is_archived` column
- **Decision**: Add `is_archived: bool` (default false) to the Memory model. User "delete" sets `is_archived = true`. Decay also uses this flag. Archived memories are excluded from retrieval and listings by default.
- **Why**: Allows undo, audit trail, and gradual cleanup. Hard deletes lose data permanently.
- **Alternatives**: Hard delete (simpler but no undo); separate `archived_memory` table (unnecessary complexity).

### 3. Memory IDs tracking through the pipeline
- **Decision**: When memories are retrieved for prompt injection, their IDs are passed through the chat graph state as `memory_ids: list[str]`. The chat endpoint includes these IDs in the `ChatResponse` as a new `used_memory_ids` field. The frontend maps IDs to memory content for badge display.
- **Why**: Minimal pipeline change. The frontend can fetch memory details lazily. No need to modify LLM prompts or parse LLM output for memory references.
- **Alternatives**: Ask the LLM to cite memory IDs in its response (unreliable); embed memory metadata in the response text (hard to parse).

### 4. Memory decay strategy: combined time-based + hard cap
- **Decision**: A background function (called on retrieval, not a scheduled job) checks: (a) memories with `last_used_at` older than `AI_MEMORY_DECAY_DAYS` (default 90) are archived; (b) if user has more than `AI_MEMORY_MAX_PER_USER` (default 500) active memories, the oldest by `last_used_at` are archived down to the limit.
- **Why**: Piggyback on existing retrieval calls avoids needing a separate scheduler/cron. Simple, works for MVP scale.
- **Alternatives**: Celery/APScheduler background job (overkill for MVP); never prune (unbounded growth).

### 5. Board-contextual memory panel
- **Decision**: A collapsible sidebar panel on the board page (similar to the task detail panel) that shows memories relevant to the board's goal. Uses the same semantic search as pipeline injection but exposes results to the user. Supports edit/delete inline.
- **Why**: Users see exactly what the AI "knows" in context. Reuses existing retrieval infrastructure.

### 6. Memory badges on chat messages
- **Decision**: The `ChatResponse` includes `used_memory_ids: list[str]`. The frontend renders small pill badges under AI messages showing truncated memory content. Clicking a badge opens the memory in a popover with full content and a link to the settings page.
- **Why**: Gives users transparency without cluttering the chat. Badges are unobtrusive and optional (hidden if empty).

### 7. Per-user memory toggle
- **Decision**: `user_settings.memory_enabled` (boolean, default true). When false, the system skips all memory extraction and retrieval for that user, regardless of the global `AI_MEMORY_ENABLED` flag. Global flag takes priority (if global is off, per-user doesn't matter).
- **Why**: Users who don't want AI memory can opt out. Follows GDPR-style data control principles.

## Risks / Trade-offs

- **Embedding API cost on edit**: Each memory edit triggers a re-embedding call (~$0.0001 per call for text-embedding-3-small). At normal usage, this is negligible. Mitigated by debouncing rapid edits on the frontend.
- **Decay on retrieval adds latency**: The decay check runs during retrieval. Mitigated by making it lightweight (single query to count + archive). Can be moved to a background task if latency becomes measurable.
- **Memory badges add payload to chat responses**: Each response includes memory IDs. Mitigated by only including IDs (not full content); frontend fetches details separately or uses cached memory list.
- **No scheduled cleanup**: Decay only runs when the user triggers a retrieval. Long-inactive users won't have memories pruned. Acceptable for MVP; add a periodic job later if needed.

## Open Questions

- None — all design decisions are resolved based on user requirements.
