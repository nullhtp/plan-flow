"""add_memory_table

Revision ID: e4f5a6b7c8d9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-17 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e4f5a6b7c8d9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "memory",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("source_goal_id", sa.String(), nullable=True),
        sa.Column("source_stage", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["source_goal_id"], ["goal.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_user_id", "memory", ["user_id"])
    op.create_index("ix_memory_source_goal_id", "memory", ["source_goal_id"])

    # Add the vector column using raw SQL (pgvector type)
    op.execute("ALTER TABLE memory ADD COLUMN embedding vector(1536)")

    # Create HNSW index for cosine similarity search
    op.execute(
        "CREATE INDEX ix_memory_embedding_hnsw ON memory "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_index("ix_memory_embedding_hnsw", table_name="memory")
    op.drop_index("ix_memory_source_goal_id", table_name="memory")
    op.drop_index("ix_memory_user_id", table_name="memory")
    op.drop_table("memory")
