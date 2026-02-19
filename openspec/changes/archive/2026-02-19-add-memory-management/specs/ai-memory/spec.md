## MODIFIED Requirements

### Requirement: Memory Data Model
The system SHALL store user memories in a `memory` PostgreSQL table with the following columns: `id` (UUID primary key), `user_id` (foreign key to `user.id`, indexed), `content` (text — the human-readable memory fact), `category` (string — one of "preference", "fact", "pattern", "context"), `embedding` (vector(1536) — pgvector column for semantic search), `source_goal_id` (nullable foreign key to `goal.id` — which goal produced this memory), `source_stage` (string — which pipeline stage produced this memory: "classification", "questions", "answers", "board_generation", "manual"), `created_at` (datetime with timezone), `last_used_at` (nullable datetime with timezone — updated when memory is retrieved for prompt injection), and `is_archived` (boolean, default false — soft-delete flag for user deletion and decay). The table SHALL have a HNSW index on the `embedding` column for efficient similarity search. The `memory` table SHALL be defined as a SQLModel model in `app/domains/ai/models.py`. All queries that list or retrieve memories for prompt injection SHALL filter by `is_archived = false` unless explicitly requesting archived memories.

#### Scenario: Memory record created after Q&A stage
- **WHEN** a user answers goal questions with "budget: under $5000"
- **THEN** a Memory row is created with content "Budget preference: under $5000", category "preference", source_stage "answers", the goal's ID as source_goal_id, is_archived false, and a vector embedding of the content

#### Scenario: Memory record tracks usage
- **WHEN** a memory is retrieved and injected into a prompt
- **THEN** the memory's `last_used_at` field is updated to the current timestamp

#### Scenario: Memory belongs to a user
- **WHEN** memories are queried
- **THEN** only memories belonging to the authenticated user are returned (filtered by `user_id`)

#### Scenario: Archived memories excluded from retrieval
- **WHEN** memories are retrieved for prompt injection or listed in the API
- **THEN** only memories with `is_archived = false` are included by default

#### Scenario: Manual source stage for user-edited memories
- **WHEN** a user edits a memory's content via the API
- **THEN** the memory's `source_stage` is updated to "manual"

### Requirement: Memory Embedding Generation
The system SHALL generate vector embeddings for each memory fact using an embedding model. The embedding model SHALL be configurable via the `AI_EMBEDDING_MODEL` environment variable (default: `openai/text-embedding-3-small`). The embedding generation function SHALL be implemented as an async utility in `app/domains/ai/memory.py`. Embedding generation SHALL use batching when multiple memories are created simultaneously (e.g., after Q&A stage extracts multiple facts). The system SHALL handle embedding API failures gracefully — if embedding generation fails, the memory SHALL be stored with a null embedding and flagged for retry. When a memory's content is edited, the system SHALL regenerate the embedding for the updated content to maintain semantic search accuracy.

#### Scenario: Single memory embedded
- **WHEN** a memory fact "Budget preference: under $5000" is created
- **THEN** the system generates a 1536-dimensional embedding vector and stores it in the memory's `embedding` column

#### Scenario: Batch embedding after Q&A
- **WHEN** the Q&A stage produces 5 memory facts
- **THEN** all 5 embeddings are generated in a single batch API call (or minimal calls) rather than 5 individual calls

#### Scenario: Embedding API failure
- **WHEN** the embedding API is unavailable or returns an error
- **THEN** the memory is stored with `embedding = NULL` and logged for later retry

#### Scenario: Re-embedding on edit
- **WHEN** a user edits a memory's content from "Budget: $3000" to "Budget: $5000-8000"
- **THEN** the system generates a new embedding for "Budget: $5000-8000" and replaces the old embedding

### Requirement: Semantic Memory Retrieval
The system SHALL retrieve the top N most relevant memories for a given context using pgvector cosine similarity search. The retrieval function SHALL accept a query string (e.g., the goal's raw input text + classification dimensions), generate an embedding for the query, and return the top N memories ordered by cosine similarity. N SHALL be configurable via the `AI_MEMORY_RETRIEVAL_LIMIT` setting (default: 15). Only memories belonging to the requesting user with `is_archived = false` SHALL be returned. The retrieval function SHALL update `last_used_at` on all returned memories. The retrieval function SHALL return both the Memory objects and their IDs for downstream tracking. The function SHALL be implemented as an async method in `app/domains/ai/memory.py`. Before performing retrieval, the function SHALL trigger a decay check (see Memory Decay requirement).

#### Scenario: Top memories retrieved for a new goal
- **WHEN** a user creates a new goal "Move from Berlin to Paris" and has 30 stored memories
- **THEN** the system generates an embedding for the query, performs cosine similarity search against non-archived memories, and returns the 15 most relevant memories with their IDs

#### Scenario: Only user's own memories retrieved
- **WHEN** user A retrieves memories for their goal
- **THEN** only memories with user_id = user A's ID are included in the search results

#### Scenario: No memories exist yet
- **WHEN** a new user creates their first goal and has no stored memories
- **THEN** the retrieval function returns an empty list

#### Scenario: Memories sorted by relevance
- **WHEN** memories are retrieved for a relocation goal
- **THEN** relocation-related memories (e.g., "Budget for relocation: $3000-5000") rank higher than unrelated memories (e.g., "Preferred programming language: Python")

#### Scenario: Archived memories excluded from retrieval
- **WHEN** a user has 20 memories but 5 are archived
- **THEN** the retrieval function only searches against the 15 non-archived memories

### Requirement: Memory Configuration
The system SHALL add the following settings to the application configuration, read from environment variables:
- `AI_EMBEDDING_MODEL` (string, default: "openai/text-embedding-3-small") — embedding model for memory vectors
- `AI_EMBEDDING_DIMENSIONS` (integer, default: 1536) — vector dimensions for the embedding column
- `AI_MEMORY_RETRIEVAL_LIMIT` (integer, default: 15) — maximum number of memories to retrieve per prompt
- `AI_MEMORY_SIMILARITY_THRESHOLD` (float, default: 0.95) — cosine similarity threshold for deduplication
- `AI_MEMORY_ENABLED` (boolean, default: true) — feature flag to disable memory system entirely
- `AI_MEMORY_DECAY_DAYS` (integer, default: 90) — number of days after which unused memories are auto-archived
- `AI_MEMORY_MAX_PER_USER` (integer, default: 500) — maximum number of active (non-archived) memories per user

#### Scenario: Default configuration
- **WHEN** no memory-related environment variables are set
- **THEN** the system uses default values: text-embedding-3-small model, 1536 dimensions, 15 retrieval limit, 0.95 dedup threshold, memory enabled, 90-day decay, 500 max per user

#### Scenario: Memory disabled via config
- **WHEN** `AI_MEMORY_ENABLED` is set to "false"
- **THEN** no memories are extracted, stored, or retrieved; pipeline operates as before without memory context

#### Scenario: Custom retrieval limit
- **WHEN** `AI_MEMORY_RETRIEVAL_LIMIT` is set to "20"
- **THEN** the system retrieves up to 20 memories per prompt injection

#### Scenario: Custom decay period
- **WHEN** `AI_MEMORY_DECAY_DAYS` is set to "30"
- **THEN** memories unused for more than 30 days are auto-archived during the decay check

### Requirement: Task Chat API Endpoint
The system SHALL expose a `POST /api/tasks/{task_id}/chat` endpoint that accepts a JSON body with `message` (string). The endpoint SHALL: load the task and its board/goal context, check the user's memory enabled setting (per-user toggle AND global flag), resolve user context server-side from the goal's stored `user_meta` via `resolve_user_context()`, retrieve relevant memories for the user (if memory is enabled), obtain the task chat tool set from the tool registry, invoke the task chat graph with the appropriate thread ID, user_context, and memory IDs, collect tool actions from the graph execution, and return the enriched chat response. The response SHALL be a JSON object conforming to the ChatResponse schema: `response` (string — the AI's reply), `thread_id` (string), `actions` (list of ToolAction objects), `pending_action_id` (nullable string), and `used_memory_ids` (list of string — IDs of memories that were injected into the prompt context for this response). The endpoint SHALL require authentication. If the task does not belong to the authenticated user's board, the endpoint SHALL return 403.

#### Scenario: Successful chat message with tool usage
- **WHEN** an authenticated user sends POST /api/tasks/{task_id}/chat with body `{"message": "What's blocking this task?"}`
- **THEN** the endpoint returns 200 with `{"response": "...", "thread_id": "task-chat-{task_id}", "actions": [...], "pending_action_id": null, "used_memory_ids": ["mem-1", "mem-2"]}`

#### Scenario: Chat message triggering confirmation
- **WHEN** an authenticated user sends POST /api/tasks/{task_id}/chat with body `{"message": "Start working on this task"}`
- **THEN** the endpoint returns 200 with the AI's response proposing the status change, `actions` containing a pending_confirmation entry, `pending_action_id` set, and `used_memory_ids` listing injected memories

#### Scenario: Unauthorized task access
- **WHEN** a user sends a chat message for a task that belongs to another user's board
- **THEN** the endpoint returns 403

#### Scenario: Task not found
- **WHEN** a user sends a chat message for a non-existent task ID
- **THEN** the endpoint returns 404

#### Scenario: Chat resolves user context from goal
- **WHEN** a user sends a task chat message for a task on a board whose goal has `user_meta` with timezone "America/Los_Angeles"
- **THEN** the endpoint resolves the user context server-side with the current date in the America/Los_Angeles timezone and passes it to the chat graph

#### Scenario: Chat without user meta (backward compatible)
- **WHEN** a user sends a task chat message for a task on a board whose goal has no `user_meta`
- **THEN** the endpoint passes an empty string as user_context and chat proceeds normally

#### Scenario: Chat with memory disabled returns empty memory IDs
- **WHEN** a user with memory disabled (per-user toggle off) sends a chat message
- **THEN** the endpoint returns `used_memory_ids: []` and no memories are retrieved or injected

## ADDED Requirements

### Requirement: Memory CRUD API
The system SHALL expose REST endpoints for managing user memories:
- `GET /api/memories` — list the authenticated user's memories with pagination, optional search query (semantic search via embedding), and optional category filter. Returns `MemoryListResponse` with `items` (list of `MemoryResponse`), `total` (int), `page` (int), `page_size` (int). Default page_size: 20. Archived memories are excluded unless `?include_archived=true` is passed.
- `GET /api/memories/{memory_id}` — get a single memory. Returns 404 if not found or not owned by user.
- `PATCH /api/memories/{memory_id}` — update a memory's content. Accepts `{"content": "new text"}`. Triggers re-embedding. Updates `source_stage` to "manual". Returns the updated `MemoryResponse`.
- `DELETE /api/memories/{memory_id}` — soft-delete a memory (sets `is_archived = true`). Returns 204.
- `DELETE /api/memories` — bulk soft-delete all of the authenticated user's active memories. Accepts optional `{"category": "preference"}` to delete by category. Returns `{"archived_count": N}`.
- `GET /api/memories/stats` — returns memory statistics: `{"total_active": N, "total_archived": N, "by_category": {"preference": N, "fact": N, ...}, "oldest_memory": "ISO date", "newest_memory": "ISO date"}`.

All endpoints SHALL require authentication. All endpoints SHALL only operate on the authenticated user's memories.

#### Scenario: List memories with pagination
- **WHEN** an authenticated user with 45 memories sends GET /api/memories?page=2&page_size=20
- **THEN** the endpoint returns memories 21-40, total 45, page 2, page_size 20

#### Scenario: Search memories semantically
- **WHEN** an authenticated user sends GET /api/memories?q=budget
- **THEN** the endpoint generates an embedding for "budget", performs cosine similarity search, and returns the most relevant memories ordered by relevance

#### Scenario: Filter by category
- **WHEN** an authenticated user sends GET /api/memories?category=preference
- **THEN** only memories with category "preference" are returned

#### Scenario: Edit memory content and re-embed
- **WHEN** an authenticated user sends PATCH /api/memories/{id} with `{"content": "Budget: $8000"}`
- **THEN** the memory content is updated, a new embedding is generated, source_stage is set to "manual", and the updated memory is returned

#### Scenario: Soft-delete single memory
- **WHEN** an authenticated user sends DELETE /api/memories/{id}
- **THEN** the memory's `is_archived` is set to true and the endpoint returns 204

#### Scenario: Bulk delete by category
- **WHEN** an authenticated user sends DELETE /api/memories with body `{"category": "pattern"}`
- **THEN** all active memories with category "pattern" are archived and `{"archived_count": N}` is returned

#### Scenario: Memory not found
- **WHEN** a user sends GET /api/memories/{non_existent_id}
- **THEN** the endpoint returns 404

#### Scenario: Cannot access another user's memory
- **WHEN** a user sends GET /api/memories/{id} for a memory owned by another user
- **THEN** the endpoint returns 404 (not 403, to avoid leaking existence)

### Requirement: User Settings Data Model
The system SHALL store per-user settings in a `user_settings` PostgreSQL table with the following columns: `id` (UUID primary key), `user_id` (foreign key to `user.id`, unique, indexed), and `memory_enabled` (boolean, default true — whether the AI memory system is active for this user). The table SHALL be defined as a SQLModel model in `app/domains/settings/models.py`. A settings row SHALL be created lazily (on first access) with defaults if it does not exist.

#### Scenario: Settings created on first access
- **WHEN** a user accesses their settings for the first time
- **THEN** a `user_settings` row is created with `memory_enabled = true`

#### Scenario: Settings row is unique per user
- **WHEN** two concurrent requests try to create settings for the same user
- **THEN** only one row is created (unique constraint on `user_id`)

### Requirement: User Settings API
The system SHALL expose REST endpoints for managing user settings:
- `GET /api/settings` — returns the authenticated user's settings. Creates default settings if none exist. Returns `UserSettingsResponse` with `memory_enabled` (bool).
- `PATCH /api/settings` — updates settings. Accepts `{"memory_enabled": false}`. Returns the updated `UserSettingsResponse`.

All endpoints SHALL require authentication.

#### Scenario: Get default settings
- **WHEN** a new user sends GET /api/settings
- **THEN** a settings row is created and `{"memory_enabled": true}` is returned

#### Scenario: Disable memory
- **WHEN** a user sends PATCH /api/settings with `{"memory_enabled": false}`
- **THEN** the setting is updated and `{"memory_enabled": false}` is returned

#### Scenario: Memory disabled blocks extraction and retrieval
- **WHEN** a user has `memory_enabled = false` and creates a new goal
- **THEN** no memories are extracted during classification, Q&A, or board generation, and no memories are retrieved for prompt injection

### Requirement: Per-User Memory Toggle Integration
The system SHALL check the per-user `memory_enabled` setting at every memory extraction and retrieval call site. The check SHALL follow this logic: if the global `AI_MEMORY_ENABLED` is false, memory is disabled for everyone regardless of per-user settings. If the global flag is true, the per-user `user_settings.memory_enabled` value determines whether memory operates for that user. The per-user setting SHALL be loaded from the database and cached for the duration of a single request.

#### Scenario: Global off overrides per-user on
- **WHEN** global `AI_MEMORY_ENABLED` is false and a user has `memory_enabled = true`
- **THEN** memory is disabled for that user

#### Scenario: Per-user off with global on
- **WHEN** global `AI_MEMORY_ENABLED` is true and a user has `memory_enabled = false`
- **THEN** memory is disabled for that user

#### Scenario: Both enabled
- **WHEN** global `AI_MEMORY_ENABLED` is true and a user has `memory_enabled = true`
- **THEN** memory operates normally for that user

### Requirement: Memory Decay
The system SHALL automatically archive stale and excess memories. The decay function SHALL be triggered during memory retrieval (piggyback, not a separate scheduler). The decay logic SHALL: (1) archive all non-archived memories where `last_used_at` (or `created_at` if `last_used_at` is null) is older than `AI_MEMORY_DECAY_DAYS` days ago; (2) if the user still has more than `AI_MEMORY_MAX_PER_USER` active memories after time-based pruning, archive the oldest by `last_used_at` until the count is at or below the limit. The decay function SHALL be implemented in `app/domains/ai/memory.py`. The decay function SHALL run at most once per user per hour (tracked via an in-memory timestamp cache) to avoid repeated expensive queries.

#### Scenario: Time-based decay archives old memories
- **WHEN** a user has 10 memories unused for 95 days (decay threshold 90) and retrieval is triggered
- **THEN** those 10 memories have `is_archived` set to true

#### Scenario: Hard cap prunes excess memories
- **WHEN** a user has 520 active memories (cap is 500) and retrieval is triggered
- **THEN** the 20 oldest memories by `last_used_at` are archived, leaving 500 active

#### Scenario: Combined decay
- **WHEN** a user has 510 memories, 30 of which are older than 90 days
- **THEN** the 30 old memories are archived first (time-based), leaving 480 active, which is under the cap, so no further pruning occurs

#### Scenario: Decay throttled to once per hour
- **WHEN** decay ran for a user 30 minutes ago and retrieval is triggered again
- **THEN** the decay check is skipped

#### Scenario: Decay does not run when memory is disabled
- **WHEN** a user has memory disabled (per-user or global)
- **THEN** the decay function is not called

### Requirement: Board-Contextual Memory Retrieval
The system SHALL provide a `GET /api/boards/{board_id}/memories` endpoint that returns memories relevant to the board's goal. The endpoint SHALL use the board's goal `original_input` as the semantic search query and return the top N memories (using the same retrieval limit as pipeline injection). The response SHALL include `MemoryResponse` objects with `id`, `content`, `category`, `source_stage`, `created_at`, `last_used_at`, and a `relevance_score` (float, cosine similarity). The endpoint SHALL require authentication and verify board ownership. This endpoint is read-only and does not modify `last_used_at`.

#### Scenario: Relevant memories returned for a board
- **WHEN** an authenticated user sends GET /api/boards/{board_id}/memories for a relocation board
- **THEN** the endpoint returns memories sorted by relevance to the relocation goal, each with a relevance_score

#### Scenario: No memories for new user
- **WHEN** a new user with no memories sends GET /api/boards/{board_id}/memories
- **THEN** the endpoint returns an empty list

#### Scenario: Unauthorized board access
- **WHEN** a user sends GET /api/boards/{board_id}/memories for another user's board
- **THEN** the endpoint returns 403
