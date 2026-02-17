# Change: Add Persistent Memory for AI Pipeline

## Why

The AI pipeline currently operates statelessly — each LLM call constructs fresh messages with no awareness of previous interactions. This means the AI cannot learn user preferences across goals, cannot carry conversation context for task-level chat, and cannot provide the "cross-goal intelligence" described in the project vision. Adding persistent memory enables the AI to produce progressively better plans by remembering user preferences, past decisions, and interaction patterns.

## What Changes

- **New `ai-memory` capability**: A memory system with two layers:
  1. **Cross-goal memory** (Memory table + pgvector): Extracts and stores structured facts from each pipeline stage (classification, Q&A, board generation). Facts are embedded for semantic similarity retrieval. Top 10-20 relevant memories injected into prompts.
  2. **Conversation state** (LangGraph PostgreSQL checkpointer): Enables persistent, thread-based conversation history for new features (task-level chat, board adaptation).
- **New dependency**: `pgvector` PostgreSQL extension + `pgvector` Python library for vector embeddings, `langgraph-checkpoint-postgres` for LangGraph checkpointing, embedding model via OpenRouter.
- **Modified `ai-pipeline` capability**: Existing pipeline nodes updated to accept and use injected memory context. Memory extraction hooks added after classification, Q&A, and board generation stages.
- **New task chat graph**: A separate LangGraph `StateGraph` for task-level AI chat, compiled with PostgreSQL checkpointer for conversation persistence.

## Impact

- Affected specs: `ai-memory` (new), `ai-pipeline` (modified)
- Affected code:
  - `backend/app/domains/ai/` — new `memory.py` service, `models.py` for Memory table, new `graphs/chat.py` for task chat
  - `backend/app/domains/ai/service.py` — memory extraction after pipeline stages, memory retrieval for prompt injection
  - `backend/app/domains/ai/nodes/` — all nodes updated to accept memory context parameter
  - `backend/app/domains/ai/prompts/` — all prompts updated to include memory section
  - `backend/app/core/config.py` — new settings for embedding model, memory limits, pgvector
  - `backend/migrations/` — new migration for Memory table with vector column
  - `docker-compose.yml` — pgvector extension for PostgreSQL
