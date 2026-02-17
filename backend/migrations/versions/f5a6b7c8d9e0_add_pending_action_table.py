"""add_pending_action_table

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-02-17 14:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_action",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_args", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pending_action_user_id", "pending_action", ["user_id"])
    op.create_index("ix_pending_action_thread_id", "pending_action", ["thread_id"])
    op.create_index(
        "ix_pending_action_thread_status",
        "pending_action",
        ["thread_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_pending_action_thread_status", table_name="pending_action")
    op.drop_index("ix_pending_action_thread_id", table_name="pending_action")
    op.drop_index("ix_pending_action_user_id", table_name="pending_action")
    op.drop_table("pending_action")
