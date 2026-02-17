"""Cross-goal memory: embedding, storage, extraction, and retrieval.

This module implements the persistent memory layer for the AI pipeline.
Memories are key-value facts extracted from pipeline stages, embedded
via OpenRouter, stored with pgvector, and retrieved by semantic similarity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from langchain_openai import OpenAIEmbeddings  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.ai.lang_utils import get_language_name
from app.domains.ai.models import Memory
from app.domains.ai.schemas import ClassificationOutput, QuestionItem

logger = logging.getLogger(__name__)


# ── Data Types ────────────────────────────────────────────


@dataclass
class MemoryInput:
    """Input for creating a memory record."""

    content: str
    category: str  # preference, fact, pattern, context
    source_stage: str  # classification, questions, answers, board_generation


# ── Embedding Generation ─────────────────────────────────


def _get_embeddings_client() -> OpenAIEmbeddings:
    """Create an OpenAI embeddings client configured for OpenRouter."""
    return OpenAIEmbeddings(
        model=settings.ai_embedding_model,
        openai_api_key=settings.openrouter_api_key,  # pyright: ignore[reportArgumentType]
        openai_api_base="https://openrouter.ai/api/v1",
        dimensions=settings.ai_embedding_dimensions,
    )


async def generate_embedding(text_input: str) -> list[float] | None:
    """Generate a vector embedding for a single text string.

    Returns None if the embedding API call fails.
    """
    try:
        client = _get_embeddings_client()
        result: list[float] = await client.aembed_query(text_input)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        return result
    except Exception:
        logger.exception("Embedding generation failed for text: %.100s", text_input)
        return None


async def generate_embeddings_batch(
    texts: list[str],
) -> list[list[float] | None]:
    """Generate embeddings for multiple texts in a single batch.

    Returns a list of embeddings (or None for failures) matching input order.
    """
    if not texts:
        return []
    try:
        client = _get_embeddings_client()
        results: list[list[float]] = await client.aembed_documents(texts)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        return results  # pyright: ignore[reportReturnType]
    except Exception:
        logger.exception("Batch embedding generation failed for %d texts", len(texts))
        return [None] * len(texts)


# ── Memory Storage & Deduplication ───────────────────────


async def store_memory(
    db: AsyncSession,
    user_id: str,
    memory_input: MemoryInput,
    source_goal_id: str | None = None,
) -> Memory:
    """Store a single memory fact with embedding and deduplication.

    If a semantically similar memory exists (cosine similarity > threshold),
    update it instead of creating a duplicate.
    """
    embedding = await generate_embedding(memory_input.content)

    # Check for duplicates if we have an embedding
    if embedding is not None:
        existing = await _find_duplicate(db, user_id, embedding)
        if existing is not None:
            existing.content = memory_input.content
            existing.last_used_at = datetime.now(UTC)
            db.add(existing)
            await db.flush()
            return existing

    memory = Memory(
        user_id=user_id,
        content=memory_input.content,
        category=memory_input.category,
        embedding=embedding,
        source_goal_id=source_goal_id,
        source_stage=memory_input.source_stage,
    )
    db.add(memory)
    await db.flush()
    return memory


async def store_memories_batch(
    db: AsyncSession,
    user_id: str,
    memory_inputs: list[MemoryInput],
    source_goal_id: str | None = None,
) -> list[Memory]:
    """Store multiple memory facts with batch embedding."""
    if not memory_inputs:
        return []

    texts = [m.content for m in memory_inputs]
    embeddings = await generate_embeddings_batch(texts)

    results: list[Memory] = []
    for mem_input, embedding in zip(memory_inputs, embeddings, strict=True):
        # Check for duplicates
        if embedding is not None:
            existing = await _find_duplicate(db, user_id, embedding)
            if existing is not None:
                existing.content = mem_input.content
                existing.last_used_at = datetime.now(UTC)
                db.add(existing)
                results.append(existing)
                continue

        memory = Memory(
            user_id=user_id,
            content=mem_input.content,
            category=mem_input.category,
            embedding=embedding,
            source_goal_id=source_goal_id,
            source_stage=mem_input.source_stage,
        )
        db.add(memory)
        results.append(memory)

    await db.flush()
    return results


async def _find_duplicate(
    db: AsyncSession,
    user_id: str,
    embedding: list[float],
) -> Memory | None:
    """Find an existing memory with cosine similarity above threshold."""
    threshold = settings.ai_memory_similarity_threshold
    # pgvector cosine distance: 1 - cosine_similarity
    # So similarity > threshold means distance < (1 - threshold)
    max_distance = 1.0 - threshold

    query = text(
        """
        SELECT id FROM memory
        WHERE user_id = :user_id
          AND embedding IS NOT NULL
          AND (embedding <=> CAST(:embedding AS vector)) < :max_distance
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT 1
        """
    )
    result = await db.execute(
        query,
        {
            "user_id": user_id,
            "embedding": str(embedding),
            "max_distance": max_distance,
        },
    )
    row = result.first()
    if row is None:
        return None

    return await db.get(Memory, row[0])


# ── Memory Extraction (Rule-Based) ──────────────────────


def extract_memories_from_classification(
    classification: ClassificationOutput,
    goal_id: str,
) -> list[MemoryInput]:
    """Extract memory facts from classification output."""
    memories: list[MemoryInput] = []

    memories.append(
        MemoryInput(
            content=f"User has worked on a {classification.domain} goal",
            category="context",
            source_stage="classification",
        )
    )

    language_name = get_language_name(classification.language)
    memories.append(
        MemoryInput(
            content=f"User's preferred language: {language_name} ({classification.language})",  # noqa: E501
            category="preference",
            source_stage="classification",
        )
    )

    if classification.dimensions:
        dims = ", ".join(classification.dimensions)
        memories.append(
            MemoryInput(
                content=f"Key dimensions for {classification.domain} goal: {dims}",
                category="context",
                source_stage="classification",
            )
        )

    return memories


def extract_memories_from_answers(
    questions: list[QuestionItem],
    answers: dict[str, Any],
    goal_id: str,
) -> list[MemoryInput]:
    """Extract memory facts from Q&A pairs."""
    memories: list[MemoryInput] = []

    question_map = {q.id: q for q in questions}
    for q_id, answer in answers.items():
        question = question_map.get(q_id)
        if question is None:
            continue

        answer_str = str(answer) if not isinstance(answer, str) else answer
        if not answer_str or answer_str == "(not answered)":
            continue

        memories.append(
            MemoryInput(
                content=f"{question.text}: {answer_str}",
                category="preference",
                source_stage="answers",
            )
        )

    return memories


def extract_memories_from_board(
    board_title: str,
    task_count: int,
    domain: str,
    goal_id: str,
) -> list[MemoryInput]:
    """Extract memory facts from board generation output."""
    return [
        MemoryInput(
            content=f"Generated a {task_count}-task {domain} plan: {board_title}",
            category="pattern",
            source_stage="board_generation",
        )
    ]


# ── Memory Retrieval (Semantic Search) ───────────────────


async def retrieve_relevant_memories(
    db: AsyncSession,
    user_id: str,
    query: str,
    limit: int | None = None,
) -> list[Memory]:
    """Retrieve the most relevant memories for a context query.

    Uses pgvector cosine similarity search. Updates last_used_at
    on retrieved memories.
    """
    if limit is None:
        limit = settings.ai_memory_retrieval_limit

    query_embedding = await generate_embedding(query)
    if query_embedding is None:
        logger.warning("Could not generate query embedding, returning no memories")
        return []

    # pgvector cosine distance ordering (lower = more similar)
    sql = text(
        """
        SELECT id FROM memory
        WHERE user_id = :user_id
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
        """
    )
    result = await db.execute(
        sql,
        {
            "user_id": user_id,
            "embedding": str(query_embedding),
            "limit": limit,
        },
    )
    rows = result.all()
    if not rows:
        return []

    memory_ids = [row[0] for row in rows]

    # Update last_used_at for retrieved memories
    now = datetime.now(UTC)
    await db.execute(
        update(Memory)
        .where(Memory.id.in_(memory_ids))  # pyright: ignore[reportUnknownMemberType]
        .values(last_used_at=now)
    )

    # Fetch full Memory objects in the same order
    memories: list[Memory] = []
    for mid in memory_ids:
        mem = await db.get(Memory, mid)
        if mem is not None:
            memories.append(mem)

    return memories
