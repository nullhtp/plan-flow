## ADDED Requirements

### Requirement: Memory Data Model
The system SHALL store user memories in a `memory` PostgreSQL table with the following columns: `id` (UUID primary key), `user_id` (foreign key to `user.id`, indexed), `content` (text — the human-readable memory fact), `category` (string — one of "preference", "fact", "pattern", "context"), `embedding` (vector(1536) — pgvector column for semantic search), `source_goal_id` (nullable foreign key to `goal.id` — which goal produced this memory), `source_stage` (string — which pipeline stage produced this memory: "classification", "questions", "answers", "board_generation"), `created_at` (datetime with timezone), and `last_used_at` (nullable datetime with timezone — updated when memory is retrieved for prompt injection). The table SHALL have a HNSW index on the `embedding` column for efficient similarity search. The `memory` table SHALL be defined as a SQLModel model in `app/domains/ai/models.py`.

#### Scenario: Memory record created after Q&A stage
- **WHEN** a user answers goal questions with "budget: under $5000"
- **THEN** a Memory row is created with content "Budget preference: under $5000", category "preference", source_stage "answers", the goal's ID as source_goal_id, and a vector embedding of the content

#### Scenario: Memory record tracks usage
- **WHEN** a memory is retrieved and injected into a prompt
- **THEN** the memory's `last_used_at` field is updated to the current timestamp

#### Scenario: Memory belongs to a user
- **WHEN** memories are queried
- **THEN** only memories belonging to the authenticated user are returned (filtered by `user_id`)

### Requirement: pgvector Extension
The system SHALL require the `pgvector` PostgreSQL extension. The Docker Compose PostgreSQL service SHALL use an image that includes pgvector (e.g., `pgvector/pgvector:pg16`). The Alembic migration that creates the `memory` table SHALL execute `CREATE EXTENSION IF NOT EXISTS vector` before creating the table. The application settings SHALL include an `ai_embedding_dimensions` setting (integer, default 1536) for configuring the vector column size.

#### Scenario: pgvector extension created in migration
- **WHEN** the memory table migration runs
- **THEN** the `vector` extension is available in PostgreSQL and the `embedding` column uses the `vector(1536)` type

#### Scenario: Docker Compose includes pgvector
- **WHEN** the developer runs `docker compose up`
- **THEN** the PostgreSQL service starts with pgvector support available

### Requirement: Memory Embedding Generation
The system SHALL generate vector embeddings for each memory fact using an embedding model. The embedding model SHALL be configurable via the `AI_EMBEDDING_MODEL` environment variable (default: `openai/text-embedding-3-small`). The embedding generation function SHALL be implemented as an async utility in `app/domains/ai/memory.py`. Embedding generation SHALL use batching when multiple memories are created simultaneously (e.g., after Q&A stage extracts multiple facts). The system SHALL handle embedding API failures gracefully — if embedding generation fails, the memory SHALL be stored with a null embedding and flagged for retry.

#### Scenario: Single memory embedded
- **WHEN** a memory fact "Budget preference: under $5000" is created
- **THEN** the system generates a 1536-dimensional embedding vector and stores it in the memory's `embedding` column

#### Scenario: Batch embedding after Q&A
- **WHEN** the Q&A stage produces 5 memory facts
- **THEN** all 5 embeddings are generated in a single batch API call (or minimal calls) rather than 5 individual calls

#### Scenario: Embedding API failure
- **WHEN** the embedding API is unavailable or returns an error
- **THEN** the memory is stored with `embedding = NULL` and logged for later retry

### Requirement: Memory Extraction After Classification
The system SHALL extract memory facts from the classification output after the goal classification pipeline stage completes. Extracted facts SHALL include: the goal's domain (e.g., "User works on goals in domain: relocation"), the detected language (e.g., "User's preferred language: Russian"), and any notable dimensions. Extraction SHALL be rule-based (deterministic), not LLM-driven. The extraction function SHALL be implemented in `app/domains/ai/memory.py`.

#### Scenario: Domain extracted as memory
- **WHEN** classification produces domain "relocation" for a user's goal
- **THEN** a memory fact is created with content "User has worked on a relocation goal", category "context", and source_stage "classification"

#### Scenario: Language preference extracted
- **WHEN** classification detects language "ru" for a user's first goal
- **THEN** a memory fact is created with content "User's preferred language: Russian (ru)", category "preference", and source_stage "classification"

#### Scenario: Duplicate domain not re-extracted
- **WHEN** a user creates a second relocation goal and the system already has a memory "User has worked on a relocation goal"
- **THEN** the system checks for semantic similarity (> 0.95) and updates the existing memory's `last_used_at` instead of creating a duplicate

### Requirement: Memory Extraction After Q&A
The system SHALL extract memory facts from user answers after each Q&A round (initial answers and follow-up answers). Each question-answer pair SHALL produce one memory fact combining the question context and the answer value (e.g., question "What is your budget?" + answer "$3000-5000" → memory "Budget for relocation: $3000-5000"). Extraction SHALL be rule-based. The extraction function SHALL deduplicate against existing memories using semantic similarity (threshold > 0.95 → update instead of insert).

#### Scenario: Answer extracted as memory fact
- **WHEN** a user answers question "What is your monthly budget?" with "$3000-5000"
- **THEN** a memory fact is created with content "Monthly budget preference: $3000-5000", category "preference", source_stage "answers"

#### Scenario: Multiple answers extracted in batch
- **WHEN** a user submits answers to 5 questions
- **THEN** up to 5 memory facts are created and their embeddings are generated in a batch

#### Scenario: Follow-up answer extracted
- **WHEN** a user submits follow-up answers
- **THEN** memory facts are extracted from the follow-up Q&A pairs with source_stage "answers"

#### Scenario: Duplicate answer updates existing memory
- **WHEN** a user answers "What is your budget?" with "$5000-8000" but a memory "Budget for relocation: $3000-5000" already exists with similarity > 0.95
- **THEN** the existing memory is updated with the new content and its `last_used_at` is refreshed

### Requirement: Memory Extraction After Board Generation
The system SHALL extract memory facts from the board generation output after board generation completes. Extracted facts SHALL include: the total task count and general board pattern (e.g., "Generated a 15-task plan for relocation with parallel housing and logistics tracks"). Extraction SHALL be rule-based. This extraction runs once per board generation, not per-task enrichment.

#### Scenario: Board pattern extracted
- **WHEN** board generation produces a 15-task DAG for a relocation goal
- **THEN** a memory fact is created with content "Generated a 15-task relocation plan", category "pattern", source_stage "board_generation"

### Requirement: Semantic Memory Retrieval
The system SHALL retrieve the top N most relevant memories for a given context using pgvector cosine similarity search. The retrieval function SHALL accept a query string (e.g., the goal's raw input text + classification dimensions), generate an embedding for the query, and return the top N memories ordered by cosine similarity. N SHALL be configurable via the `AI_MEMORY_RETRIEVAL_LIMIT` setting (default: 15). Only memories belonging to the requesting user SHALL be returned. The retrieval function SHALL update `last_used_at` on all returned memories. The function SHALL be implemented as an async method in `app/domains/ai/memory.py`.

#### Scenario: Top memories retrieved for a new goal
- **WHEN** a user creates a new goal "Move from Berlin to Paris" and has 30 stored memories
- **THEN** the system generates an embedding for the query, performs cosine similarity search, and returns the 15 most relevant memories

#### Scenario: Only user's own memories retrieved
- **WHEN** user A retrieves memories for their goal
- **THEN** only memories with user_id = user A's ID are included in the search results

#### Scenario: No memories exist yet
- **WHEN** a new user creates their first goal and has no stored memories
- **THEN** the retrieval function returns an empty list

#### Scenario: Memories sorted by relevance
- **WHEN** memories are retrieved for a relocation goal
- **THEN** relocation-related memories (e.g., "Budget for relocation: $3000-5000") rank higher than unrelated memories (e.g., "Preferred programming language: Python")

### Requirement: Memory Prompt Formatting
The system SHALL format retrieved memories into a prompt-injectable text block, following the same pattern as the existing "User context" block. The format SHALL be:

```
Relevant memories from past interactions:
- {memory_1_content}
- {memory_2_content}
- ...
```

If no memories are available, the block SHALL be omitted entirely (not an empty section). The formatting function SHALL be implemented in `app/domains/ai/prompts/memory.py`.

#### Scenario: Memories formatted for prompt injection
- **WHEN** 5 memories are retrieved for prompt injection
- **THEN** a text block is produced with the header "Relevant memories from past interactions:" followed by each memory as a bullet point

#### Scenario: No memories produces no block
- **WHEN** zero memories are retrieved
- **THEN** the formatting function returns an empty string (no "Relevant memories" section in the prompt)

### Requirement: Memory Configuration
The system SHALL add the following settings to the application configuration, read from environment variables:
- `AI_EMBEDDING_MODEL` (string, default: "openai/text-embedding-3-small") — embedding model for memory vectors
- `AI_EMBEDDING_DIMENSIONS` (integer, default: 1536) — vector dimensions for the embedding column
- `AI_MEMORY_RETRIEVAL_LIMIT` (integer, default: 15) — maximum number of memories to retrieve per prompt
- `AI_MEMORY_SIMILARITY_THRESHOLD` (float, default: 0.95) — cosine similarity threshold for deduplication
- `AI_MEMORY_ENABLED` (boolean, default: true) — feature flag to disable memory system entirely

#### Scenario: Default configuration
- **WHEN** no memory-related environment variables are set
- **THEN** the system uses default values: text-embedding-3-small model, 1536 dimensions, 15 retrieval limit, 0.95 dedup threshold, memory enabled

#### Scenario: Memory disabled via config
- **WHEN** `AI_MEMORY_ENABLED` is set to "false"
- **THEN** no memories are extracted, stored, or retrieved; pipeline operates as before without memory context

#### Scenario: Custom retrieval limit
- **WHEN** `AI_MEMORY_RETRIEVAL_LIMIT` is set to "20"
- **THEN** the system retrieves up to 20 memories per prompt injection

### Requirement: LangGraph PostgreSQL Checkpointer
The system SHALL configure a LangGraph PostgreSQL checkpointer using the `langgraph-checkpoint-postgres` library. The checkpointer SHALL use the same PostgreSQL database as the application (connection string from `DATABASE_URL`). The checkpointer SHALL be initialized as a shared async instance at application startup and shut down gracefully on application shutdown. The checkpointer's internal tables SHALL be created via its own setup method (not Alembic-managed). The checkpointer instance SHALL be available as a dependency for LangGraph graphs that need conversation persistence.

#### Scenario: Checkpointer initialized at startup
- **WHEN** the application starts
- **THEN** the LangGraph PostgreSQL checkpointer is initialized with the application's database connection and its internal tables are created

#### Scenario: Checkpointer shared across graphs
- **WHEN** a task chat graph needs conversation persistence
- **THEN** it receives the shared checkpointer instance via dependency injection

#### Scenario: Checkpointer shut down gracefully
- **WHEN** the application shuts down
- **THEN** the checkpointer's database connections are properly closed

### Requirement: Task Chat Graph
The system SHALL implement a LangGraph `StateGraph` for task-level AI chat, compiled with the PostgreSQL checkpointer. The chat graph state SHALL include: `messages` (list of chat messages), `task_id` (string), `task_context` (string — task title, description, subtasks, board context), `memory_context` (string — formatted memory block), and `goal_context` (string — goal text and classification summary). The graph SHALL have a single `respond` node that produces an AI response given the conversation history and context. Each task's chat session SHALL use a thread ID of format `task-chat-{task_id}`, enabling conversation persistence across HTTP requests. The graph SHALL be defined in `app/domains/ai/graphs/chat.py`.

#### Scenario: First message in task chat
- **WHEN** a user sends the first chat message for task "t1" (thread "task-chat-t1")
- **THEN** the graph creates a new thread, injects task context and memory context, and produces an AI response

#### Scenario: Resuming task chat
- **WHEN** a user sends a second message to task "t1" after a previous conversation
- **THEN** the graph loads the existing thread state (including previous messages) from the checkpointer and continues the conversation

#### Scenario: Task context included in chat
- **WHEN** a user chats about task "Research neighborhoods in Lisbon"
- **THEN** the AI response demonstrates awareness of the task's title, description, subtasks, and the parent goal's context

#### Scenario: Memory context included in chat
- **WHEN** a user with stored memories chats about a task
- **THEN** the AI response MAY reference relevant memories (e.g., "Based on your previous preference for tight budgets...")

### Requirement: Task Chat API Endpoint
The system SHALL expose a `POST /api/tasks/{task_id}/chat` endpoint that accepts a JSON body with `message` (string). The endpoint SHALL: load the task and its board/goal context, retrieve relevant memories for the user, invoke the task chat graph with the appropriate thread ID, and return the AI response. The response SHALL be a JSON object with `response` (string — the AI's reply) and `thread_id` (string). The endpoint SHALL require authentication. If the task does not belong to the authenticated user's board, the endpoint SHALL return 403.

#### Scenario: Successful chat message
- **WHEN** an authenticated user sends POST /api/tasks/{task_id}/chat with body `{"message": "How should I start this task?"}`
- **THEN** the endpoint returns 200 with `{"response": "...", "thread_id": "task-chat-{task_id}"}`

#### Scenario: Unauthorized task access
- **WHEN** a user sends a chat message for a task that belongs to another user's board
- **THEN** the endpoint returns 403

#### Scenario: Task not found
- **WHEN** a user sends a chat message for a non-existent task ID
- **THEN** the endpoint returns 404
