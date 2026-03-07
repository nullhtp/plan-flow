"""add_board_share_and_board_member_tables

Revision ID: d4e5f6a7b8c9
Revises: c7a1b2d3e4f5
Create Date: 2026-03-07 10:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c7a1b2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "board_share",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("board_id", sa.String(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["board.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("board_id"),
    )
    op.create_index("ix_board_share_token", "board_share", ["token"], unique=True)

    op.create_table(
        "board_member",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("board_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="collaborator"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["board.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("board_id", "user_id", name="uq_board_member_board_user"),
    )
    op.create_index("ix_board_member_board_id", "board_member", ["board_id"])
    op.create_index("ix_board_member_user_id", "board_member", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_board_member_user_id", table_name="board_member")
    op.drop_index("ix_board_member_board_id", table_name="board_member")
    op.drop_table("board_member")
    op.drop_index("ix_board_share_token", table_name="board_share")
    op.drop_table("board_share")
