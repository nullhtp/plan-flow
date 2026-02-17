from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy import Column, DateTime, Index, Text
from sqlmodel import Field, SQLModel

from app.core.config import settings


class Memory(SQLModel, table=True):
    """A stored memory fact for cross-goal AI intelligence."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    user_id: str = Field(foreign_key="user.id", index=True)
    content: str = Field(sa_column=Column(Text, nullable=False))
    category: str = Field(
        description="One of: preference, fact, pattern, context",
    )
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(
            Vector(settings.ai_embedding_dimensions),  # pyright: ignore[reportUnknownArgumentType]
            nullable=True,
        ),
    )
    source_goal_id: str | None = Field(
        default=None,
        foreign_key="goal.id",
        index=True,
    )
    source_stage: str = Field(
        description="Pipeline stage: classification, questions, answers, board_generation",  # noqa: E501
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    __table_args__ = (
        Index(
            "ix_memory_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
