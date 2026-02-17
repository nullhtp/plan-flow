## Context

PlanFlow's AI pipeline is entirely stateless. Each LLM call constructs fresh messages with no awareness of the user's history. The project vision describes "cross-goal intelligence" — the AI should remember user context across goals — and "AI-assisted execution" — task-level chat that requires persistent conversation state. Neither exists today.

The current `service.py` bypasses LangGraph entirely, calling node functions directly. The LangGraph `StateGraph` is defined in `pipeline.py` but never compiled or invoked. State is accumulated in `Goal.ai_context` (a JSON column) but this is a per-goal, flat key-value blob — not a conversation history or cross-goal memory.

### Stakeholders
- Solo developer (project owner)
- End users who benefit from AI that improves over time

### Constraints
- PostgreSQL is the only database (no Redis, no separate vector DB)
- OpenRouter is the LLM gateway (embedding models must be available there or via a separate provider)
- MVP timeline: keep implementation simple and iterative
- Cost-sensitive: minimize extra LLM calls for memory extraction

## Goals / Non-Goals

### Goals
- Cross-goal memory: AI remembers user preferences, past decisions, and patterns across all goals
- Per-goal conversation state: persistent chat history for task-level AI chat and board adaptation
- Memory-enhanced pipeline: existing classification, question generation, and board generation use relevant memories
- Automatic memory extraction: no manual user action needed to build memory

### Non-Goals
- User-facing memory management UI (no view/edit/delete for MVP)
- Memory sharing between users
- Real-time memory updates during streaming (memories are extracted after pipeline stages complete)
- Refactoring the existing goal pipeline to use LangGraph invocation (keep direct node calls as-is)

## Decisions

### Decision 1: Two-Layer Memory Architecture

**What:** Use two separate persistence mechanisms:
1. **Memory table with pgvector** — for cross-goal fact storage and semantic retrieval
2. **LangGraph PostgreSQL checkpointer** — for per-conversation thread state (task chat, board adaptation)

**Why:** These serve different purposes. Cross-goal memory is a growing collection of user facts that need semantic search. Conversation state is a linear message history per thread that needs checkpointing. Mixing them in one system would be awkward.

**Alternatives considered:**
- *Single Memory table for everything:* Would require storing raw chat messages alongside extracted facts. Semantic search over chat transcripts is noisy.
- *LangGraph checkpointer for everything:* Checkpointers store graph state snapshots, not extracted facts. Cross-goal queries ("what does this user prefer?") don't map to the checkpointer's thread model.
- *PostgreSQL only (no pgvector):* Would work with keyword/category matching but loses semantic relevance. User chose pgvector.

### Decision 2: Semantic Retrieval with pgvector

**What:** Each memory fact is stored with a vector embedding. Retrieval uses cosine similarity between the current context (goal text + classification dimensions) and stored memory embeddings to find the top 10-20 most relevant facts.

**Why:** User explicitly chose semantic similarity over category+recency matching. pgvector keeps everything in PostgreSQL — no separate vector DB needed.

**Embedding model:** Use `openai/text-embedding-3-small` via OpenRouter's embeddings API (`POST /api/v1/embeddings`). OpenRouter supports embeddings natively with the same API key and base URL used for chat completions. The implementation uses LangChain's `OpenAIEmbeddings` class configured with the OpenRouter base URL — the same pattern as the existing `ChatOpenAI` client. Batch embedding (multiple texts in one request) is supported.

**Vector dimensions:** 1536 (OpenAI text-embedding-3-small default) or configurable.

### Decision 3: Keep Existing Pipeline, Add LangGraph for New Features Only

**What:** The existing goal pipeline (classify → questions → board generation) continues to call nodes directly via `service.py`. LangGraph with checkpointer is used ONLY for new features: task-level chat graph and board adaptation graph.

**Why:** The existing pipeline works and is well-tested. Refactoring it to use LangGraph invocation adds risk with no functional benefit. New features (chat, adaptation) naturally benefit from LangGraph's conversation threading.

**Alternatives considered:**
- *Refactor everything to LangGraph:* High risk, breaks working code, no user-facing benefit.
- *No LangGraph at all:* Would require building conversation threading from scratch for task chat.

### Decision 4: LLM-Free Memory Extraction (Rule-Based)

**What:** Extract memories from structured pipeline outputs using deterministic rules, not additional LLM calls:
- After classification: extract `domain`, `complexity`, `language` as facts
- After Q&A: extract each answer as a fact (e.g., "budget_preference: under $5000")
- After board generation: extract `task_count`, `board_complexity_pattern` as facts

**Why:** Minimizes API costs and latency. Pipeline outputs are already structured (Pydantic models), so extraction is straightforward. The Q&A stage in particular already produces clean key-value facts (question text → answer text).

**Alternatives considered:**
- *LLM-driven extraction:* More intelligent but adds 1 LLM call per pipeline stage per goal. Cost and latency concern.
- *End-of-lifecycle only:* Memories wouldn't be available until goal completion — useless for in-progress context.

### Decision 5: Memory Injection via Prompt Section

**What:** Retrieved memories are formatted as a "Memory context" section appended to user prompts (similar to the existing "User context" block). Format:

```
Relevant user memories:
- Previously relocated from Berlin to Lisbon (goal completed 2025-12-15)
- Budget preference: tight, under $5000
- Has pets: 2 cats, need pet transport
- Prefers morning deadlines
- Works remotely, flexible schedule
```

**Why:** Simple, transparent, and works with any LLM. The existing pipeline already uses a "User context" prompt block pattern — this follows the same convention.

### Decision 6: Separate Task Chat Graph

**What:** Create a new LangGraph `StateGraph` at `app/domains/ai/graphs/chat.py` specifically for task-level AI chat. This graph is compiled with the `PostgresSaver` checkpointer, giving each task-chat session a persistent thread.

**Why:** Clean separation from the goal pipeline. The chat graph has different state requirements (message history, task context) and a different lifecycle (long-running conversation vs. one-shot pipeline).

**Thread ID convention:** `task-chat-{task_id}` — one thread per task, allowing conversation to resume across sessions.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| pgvector extension not available in all PostgreSQL deployments | Deployment failures | Document requirement; add Docker Compose config; provide fallback to cosine similarity in Python (slower) |
| Embedding API costs accumulate | Budget concern | Use cheapest embedding model; batch embeddings where possible; cache embeddings |
| Memory injection increases prompt token count | Higher LLM costs per call | Cap at 10-20 memories; monitor token usage; make limit configurable |
| Stale or incorrect memories degrade AI quality | Poor user experience | Add memory staleness tracking (last_used, created_at); consider TTL or confidence decay |
| LangGraph checkpointer schema conflicts with app migrations | Migration complexity | Use separate schema/table prefix for checkpointer tables; document Alembic coexistence |

## Migration Plan

1. **Add pgvector extension** to Docker Compose PostgreSQL service (`CREATE EXTENSION IF NOT EXISTS vector`)
2. **Create Memory table** via Alembic migration (id, user_id, content, category, embedding vector, source_goal_id, source_stage, created_at, last_used_at)
3. **Initialize LangGraph checkpointer** tables (managed by `langgraph-checkpoint-postgres`, separate from Alembic)
4. **Deploy memory extraction** — starts building memory from new goals; no backfill of existing goals
5. **Deploy memory injection** — existing pipeline starts using memories for new goals
6. **Deploy task chat** — new endpoint, no impact on existing features

Rollback: Each step is independently reversible. Memory extraction/injection can be disabled via config flag without schema changes.

## Open Questions

1. ~~**Embedding model availability on OpenRouter:**~~ **Resolved.** OpenRouter supports embeddings natively via `POST /api/v1/embeddings`. Same API key, same base URL. `openai/text-embedding-3-small` is available. No additional provider or API key needed.
2. **pgvector index strategy:** IVFFlat vs HNSW index for the embedding column. HNSW is better for small-to-medium datasets (our case) but uses more memory.
3. **Memory deduplication:** If a user creates similar goals, extraction may produce duplicate facts. Strategy: check for semantic similarity before inserting (above 0.95 similarity → update existing instead of insert).
4. **Checkpointer table management:** `langgraph-checkpoint-postgres` creates its own tables. Need to verify these don't conflict with Alembic's migration tracking.
