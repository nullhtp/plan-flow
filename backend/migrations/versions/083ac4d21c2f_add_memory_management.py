"""add_memory_management

Revision ID: 083ac4d21c2f
Revises: b2f3c4d5e6f7
Create Date: 2026-02-19 10:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "083ac4d21c2f"
down_revision = "b2f3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_archived column to memory table
    op.add_column(
        "memory",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create user_settings table
    op.create_table(
        "user_settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "memory_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "ix_user_settings_user_id", "user_settings", ["user_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")
    op.drop_column("memory", "is_archived")
