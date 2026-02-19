## 1. Backend: Data Model & Migration

- [x] 1.1 Add `is_archived` column to Memory model in `app/domains/ai/models.py`
- [x] 1.2 Add `source_stage = "manual"` to the allowed source stages
- [x] 1.3 Create `app/domains/settings/` domain with `models.py` (UserSettings SQLModel), `schemas.py`, `repository.py`, `service.py`, `router.py`
- [x] 1.4 Create Alembic migration: add `is_archived` to `memory` table, create `user_settings` table
- [x] 1.5 Add new config settings to `app/core/config.py`: `AI_MEMORY_DECAY_DAYS`, `AI_MEMORY_MAX_PER_USER`

## 2. Backend: Memory CRUD API

- [x] 2.1 Create memory schemas in `app/domains/ai/schemas.py`: `MemoryResponse`, `MemoryListResponse`, `MemoryUpdateRequest`, `MemoryBulkDeleteRequest`, `MemoryStatsResponse`
- [x] 2.2 Create memory repository in `app/domains/ai/memory_repository.py`: list, get, update, soft-delete, bulk-soft-delete, stats queries (all filter `is_archived = false` by default)
- [x] 2.3 Create memory management service in `app/domains/ai/memory_service.py`: CRUD with re-embedding on edit, ownership checks
- [x] 2.4 Add memory management routes to `app/domains/ai/router.py` (or new `memory_router.py`): GET /api/memories, GET /api/memories/stats, GET /api/memories/{id}, PATCH /api/memories/{id}, DELETE /api/memories/{id}, DELETE /api/memories
- [x] 2.5 Write tests for memory CRUD endpoints (list, search, edit, delete, bulk-delete, stats)

## 3. Backend: User Settings API

- [x] 3.1 Implement UserSettings repository with lazy creation (get-or-create pattern)
- [x] 3.2 Implement settings service with get and update
- [x] 3.3 Add routes: GET /api/settings, PATCH /api/settings
- [x] 3.4 Register settings router in `app/main.py`
- [x] 3.5 Write tests for settings endpoints

## 4. Backend: Per-User Memory Toggle

- [x] 4.1 Create helper function `is_memory_enabled(db, user_id)` that checks both global flag and per-user setting
- [x] 4.2 Update all memory extraction call sites (goals/service.py, boards/task_service.py) to use the helper
- [x] 4.3 Update all memory retrieval call sites (ai/router.py, boards/router.py, goals/service.py) to use the helper
- [x] 4.4 Write tests for per-user toggle logic (global off overrides, per-user off, both on)

## 5. Backend: Memory Decay

- [x] 5.1 Implement decay function in `app/domains/ai/memory.py`: time-based archival + hard cap pruning
- [x] 5.2 Add in-memory per-user throttle (once per hour) to avoid repeated decay queries
- [x] 5.3 Call decay function at the start of `retrieve_relevant_memories`
- [x] 5.4 Update `retrieve_relevant_memories` to filter `is_archived = false`
- [x] 5.5 Write tests for decay (time-based, cap-based, combined, throttle)

## 6. Backend: Memory IDs in Chat Response

- [x] 6.1 Add `used_memory_ids: list[str]` field to `ChatResponse` schema (default empty list)
- [x] 6.2 Update `retrieve_relevant_memories` to return memory IDs alongside Memory objects
- [x] 6.3 Pass memory IDs through chat graph state (`memory_ids` field in TaskChatState and BoardChatState)
- [x] 6.4 Update task chat endpoint to extract memory IDs and include in response
- [x] 6.5 Update board chat endpoint to extract memory IDs and include in response
- [x] 6.6 Add board-contextual memory endpoint: GET /api/boards/{board_id}/memories
- [x] 6.7 Write tests for memory IDs in chat response

## 7. Frontend: API Client Regeneration

- [x] 7.1 Run Orval to regenerate TypeScript types and React Query hooks from updated OpenAPI spec
- [x] 7.2 Verify new types: MemoryResponse, MemoryListResponse, UserSettingsResponse, updated ChatResponse with used_memory_ids

## 8. Frontend: Settings Page

- [x] 8.1 Create settings route `/settings` with TanStack Router (auth-protected)
- [x] 8.2 Add "Settings" link to user menu/avatar dropdown in app header
- [x] 8.3 Create SettingsPage component with Memory section layout
- [x] 8.4 Implement memory toggle switch (GET/PATCH /api/settings, optimistic update)
- [x] 8.5 Implement memory statistics display (GET /api/memories/stats)
- [x] 8.6 Implement memory list with pagination (GET /api/memories with page/page_size)
- [x] 8.7 Implement memory search (semantic search via q parameter)
- [x] 8.8 Implement category filter dropdown
- [x] 8.9 Implement inline memory edit (PATCH /api/memories/{id}, optimistic)
- [x] 8.10 Implement single memory delete (DELETE /api/memories/{id}, optimistic with confirmation)
- [x] 8.11 Implement "Clear All Memories" button with confirmation dialog (DELETE /api/memories)
- [x] 8.12 Implement category-specific clear ("Clear filtered")

## 9. Frontend: Board Memory Sidebar

- [x] 9.1 Add memory icon button to board toolbar
- [x] 9.2 Create BoardMemorySidebar component (collapsible panel)
- [x] 9.3 Fetch relevant memories via GET /api/boards/{board_id}/memories
- [x] 9.4 Display memory items with content, category badge, relevance score indicator
- [x] 9.5 Implement inline edit and delete (same behavior as settings)
- [x] 9.6 Add "Manage all memories" link to /settings

## 10. Frontend: Memory Badges on Chat Messages

- [x] 10.1 Update AI message component to accept and render `used_memory_ids`
- [x] 10.2 Implement memory badge pill component (truncated content, category color)
- [x] 10.3 Implement badge click popover (full content, category, "View in Settings" link)
- [x] 10.4 Implement memory cache resolution (check React Query cache, lazy fetch on miss)
- [x] 10.5 Handle deleted memory badge state ("Memory removed")
- [x] 10.6 Apply badges to both task chat and board chat message components

## 11. Testing & Validation

- [x] 11.1 Backend integration tests for full memory management flow
- [x] 11.2 Frontend component tests for settings page (toggle, list, edit, delete)
- [x] 11.3 Frontend component tests for memory badges
- [x] 11.4 Manual E2E verification: create memories via goal flow, view in settings, edit, delete, verify chat badges
