# Change: Add User-Facing Memory Management

## Why
The AI memory system silently stores facts about users (preferences, past goals, patterns) but provides zero visibility or control. Users cannot see what the AI "remembers," delete incorrect memories, edit outdated facts, or toggle the feature off. This is a transparency and trust problem — users should own their data and understand how the AI personalizes their experience.

## What Changes
- **Memory CRUD API**: New REST endpoints for listing, viewing, editing, and deleting memories (`GET/PATCH/DELETE /api/memories`)
- **Memory Settings API**: New endpoint for per-user memory toggle (`GET/PUT /api/settings/memory`)
- **Memory decay system**: Background cleanup of unused/stale memories with configurable TTL and hard cap per user
- **Settings page (frontend)**: New `/settings` route with a "Memory" section showing all stored memories with search, edit, delete, bulk-clear, and on/off toggle
- **Contextual memory panel (frontend)**: Memory sidebar on board pages showing memories relevant to the current goal, with edit/delete
- **Memory badges on chat messages**: AI chat messages display clickable badges showing which memories were used to generate the response
- **Re-embedding on edit**: Editing memory content regenerates the embedding vector for accurate future retrieval
- **Per-user memory toggle**: User-level setting (in DB) to disable memory, overriding the global `AI_MEMORY_ENABLED` flag

## Impact
- Affected specs: `ai-memory`, `task-chat-ui`, new `memory-management-ui`
- Affected code:
  - Backend: `app/domains/ai/memory.py`, `app/domains/ai/models.py`, `app/domains/ai/router.py`, `app/core/config.py`, new `app/domains/settings/` domain
  - Frontend: new `src/features/settings/`, new `src/features/memory/`, modified `src/features/ai-chat/`, modified `src/features/board/`
  - Database: new migration for `user_settings` table, modified memory model for `is_archived` soft-delete column
  - API spec: new endpoints, modified chat response schema
