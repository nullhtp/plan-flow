"""add_artifact_table

Revision ID: eb35d52da786
Revises: f5a6b7c8d9e0
Create Date: 2026-02-18 10:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "eb35d52da786"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "content_type",
            sa.String(50),
            nullable=False,
            server_default="text/markdown",
        ),
        sa.Column("created_by", sa.String(20), nullable=False, server_default="ai"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifact_task_id", "artifact", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_artifact_task_id", table_name="artifact")
    op.drop_table("artifact")
