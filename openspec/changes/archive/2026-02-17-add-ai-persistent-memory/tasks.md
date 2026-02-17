## 1. Infrastructure & Dependencies

- [ ] 1.1 Add Python dependencies: `pgvector`, `langgraph-checkpoint-postgres` to `pyproject.toml`
- [ ] 1.2 Update Docker Compose PostgreSQL service to use `pgvector/pgvector:pg16` image
- [ ] 1.3 Add memory-related settings to `app/core/config.py`: `ai_embedding_model`, `ai_embedding_dimensions`, `ai_memory_retrieval_limit`, `ai_memory_similarity_threshold`, `ai_memory_enabled`

## 2. Memory Data Model & Migration

- [ ] 2.1 Create `Memory` SQLModel in `app/domains/ai/models.py` with fields: id, user_id, content, category, embedding (vector), source_goal_id, source_stage, created_at, last_used_at
- [ ] 2.2 Create Alembic migration: `CREATE EXTENSION IF NOT EXISTS vector` + `memory` table with HNSW index on embedding column
- [ ] 2.3 Verify migration runs cleanly against local PostgreSQL (up and down)

## 3. Embedding Generation

- [ ] 3.1 Implement `generate_embedding(text: str) -> list[float]` async function in `app/domains/ai/memory.py` using the configured embedding model
- [ ] 3.2 Implement `generate_embeddings_batch(texts: list[str]) -> list[list[float]]` for batch embedding generation
- [ ] 3.3 Handle embedding API failures gracefully (store with null embedding, log for retry)
- [ ] 3.4 Write unit tests for embedding generation (mock the API call, verify dimensions and error handling)

## 4. Memory Storage & Deduplication

- [ ] 4.1 Implement `store_memory(db, user_id, content, category, source_goal_id, source_stage) -> Memory` in `app/domains/ai/memory.py` — generates embedding and inserts
- [ ] 4.2 Implement deduplication check: before insert, query for existing memories with cosine similarity > 0.95; if found, update `last_used_at` and optionally `content` instead of inserting
- [ ] 4.3 Implement `store_memories_batch(db, user_id, memories: list[MemoryInput]) -> list[Memory]` for batch storage with batch embedding
- [ ] 4.4 Write unit tests for storage and deduplication logic

## 5. Memory Extraction (Rule-Based)

- [ ] 5.1 Implement `extract_memories_from_classification(classification: ClassificationOutput, goal_id: str) -> list[MemoryInput]` — extracts domain, language facts
- [ ] 5.2 Implement `extract_memories_from_answers(questions, answers, goal_id: str) -> list[MemoryInput]` — extracts each Q&A pair as a fact
- [ ] 5.3 Implement `extract_memories_from_board(board_title: str, task_count: int, goal_id: str) -> list[MemoryInput]` — extracts board pattern facts
- [ ] 5.4 Write unit tests for all extraction functions (verify correct content, category, source_stage)

## 6. Memory Retrieval (Semantic Search)

- [ ] 6.1 Implement `retrieve_relevant_memories(db, user_id, query: str, limit: int) -> list[Memory]` using pgvector cosine similarity search
- [ ] 6.2 Update `last_used_at` on retrieved memories
- [ ] 6.3 Write integration tests for retrieval (insert test memories, verify ranking by similarity)

## 7. Memory Prompt Formatting

- [ ] 7.1 Create `app/domains/ai/prompts/memory.py` with `format_memory_block(memories: list[Memory]) -> str` function
- [ ] 7.2 Return empty string when memories list is empty
- [ ] 7.3 Write unit tests for formatting (verify output format, empty case)

## 8. Pipeline Integration — Memory Injection

- [ ] 8.1 Update `classify_and_generate_questions()` in `service.py`: retrieve memories before question generation, pass memory context to `generate_questions` node
- [ ] 8.2 Update `generate_questions` node in `nodes/questions.py`: accept `memory_context` parameter, append to user prompt
- [ ] 8.3 Update `generate_follow_up_questions` in `nodes/questions.py`: accept and use `memory_context` parameter
- [ ] 8.4 Update `generate_board_stream()` in `service.py`: retrieve memories, pass memory context to skeleton and enrichment nodes
- [ ] 8.5 Update `generate_board_skeleton` node in `nodes/generate_board.py`: accept `memory_context` parameter, append to user prompt
- [ ] 8.6 Update `enrich_task` node in `nodes/enrich_task.py`: accept `memory_context` parameter, append to user prompt
- [ ] 8.7 Update `GoalPipelineState` in `pipeline.py`: add `memory_context` field
- [ ] 8.8 Ensure all prompt modules place memory block after user meta block

## 9. Pipeline Integration — Memory Extraction Hooks

- [ ] 9.1 Add memory extraction call in `classify_and_generate_questions()` after successful classification
- [ ] 9.2 Add memory extraction call in goals router/service after user submits answers (initial and follow-up)
- [ ] 9.3 Add memory extraction call in `generate_board_stream()` after `generation_complete` event
- [ ] 9.4 Ensure extraction does not block the response (run after yielding events or as background task)

## 10. Feature Flag & Backward Compatibility

- [ ] 10.1 Gate all memory operations behind `ai_memory_enabled` config flag
- [ ] 10.2 When disabled: skip extraction, skip retrieval, pass empty memory context to nodes
- [ ] 10.3 Write integration tests: verify pipeline works identically with memory disabled

## 11. LangGraph Checkpointer Setup

- [ ] 11.1 Implement checkpointer initialization in `app/core/checkpointer.py` (or `app/domains/ai/checkpointer.py`): create `AsyncPostgresSaver` instance from DATABASE_URL
- [ ] 11.2 Add checkpointer lifecycle to FastAPI startup/shutdown events (init on startup, close on shutdown)
- [ ] 11.3 Expose checkpointer as a FastAPI dependency
- [ ] 11.4 Verify checkpointer tables are created on first startup (separate from Alembic)

## 12. Task Chat Graph

- [ ] 12.1 Define `TaskChatState` TypedDict in `app/domains/ai/graphs/chat.py`: messages, task_id, task_context, memory_context, goal_context
- [ ] 12.2 Implement `respond` node: constructs system prompt with task/goal/memory context, invokes LLM with conversation history
- [ ] 12.3 Create chat system prompt in `app/domains/ai/prompts/chat.py`
- [ ] 12.4 Build and compile the `task_chat_graph` with PostgreSQL checkpointer
- [ ] 12.5 Implement thread ID convention: `task-chat-{task_id}`

## 13. Task Chat API Endpoint

- [ ] 13.1 Create `POST /api/tasks/{task_id}/chat` endpoint in `app/domains/ai/router.py` (new file) or extend `app/domains/boards/router.py`
- [ ] 13.2 Implement request/response schemas: `TaskChatRequest(message: str)`, `TaskChatResponse(response: str, thread_id: str)`
- [ ] 13.3 Load task + board + goal context for the chat graph
- [ ] 13.4 Retrieve relevant memories for the user
- [ ] 13.5 Invoke chat graph with thread config `{"configurable": {"thread_id": "task-chat-{task_id}"}}`
- [ ] 13.6 Add authorization check: task must belong to user's board
- [ ] 13.7 Register the new router in `main.py`

## 14. Testing

- [ ] 14.1 Unit tests for memory model (CRUD operations)
- [ ] 14.2 Unit tests for embedding generation (mocked)
- [ ] 14.3 Integration tests for semantic retrieval (pgvector similarity search)
- [ ] 14.4 Integration tests for memory extraction hooks (verify memories created after each pipeline stage)
- [ ] 14.5 Integration tests for memory injection into pipeline nodes (verify memory context appears in prompts)
- [ ] 14.6 Integration tests for task chat endpoint (create task, send messages, verify conversation persistence)
- [ ] 14.7 Integration tests for chat authorization (verify 403 for other user's tasks)
- [ ] 14.8 End-to-end test: create goal → classify → answer questions → generate board → verify memories extracted → create new goal → verify memories injected into prompts

## 15. Documentation & Configuration

- [ ] 15.1 Add memory-related environment variables to `.env.example`
- [ ] 15.2 Document pgvector requirement in Docker Compose comments
- [ ] 15.3 Update OpenAPI spec (auto-generated) with new chat endpoint
