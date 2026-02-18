"""add_board_parent_task_id

Revision ID: b2f3c4d5e6f7
Revises: a1f2b3c4d5e6
Create Date: 2026-02-18 18:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2f3c4d5e6f7"
down_revision = "a1f2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable parent_task_id FK to board table
    op.add_column(
        "board",
        sa.Column("parent_task_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_board_parent_task_id",
        "board",
        "task",
        ["parent_task_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_board_parent_task_id",
        "board",
        ["parent_task_id"],
        unique=True,
    )

    # Make goal_id nullable (sub-boards don't have a direct goal)
    op.alter_column(
        "board",
        "goal_id",
        existing_type=sa.String(),
        nullable=True,
    )

    # Add check constraint: at least one of goal_id or parent_task_id must be set
    op.create_check_constraint(
        "ck_board_goal_or_parent_task",
        "board",
        "goal_id IS NOT NULL OR parent_task_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_board_goal_or_parent_task", "board", type_="check")
    op.alter_column(
        "board",
        "goal_id",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_index("ix_board_parent_task_id", table_name="board")
    op.drop_constraint("fk_board_parent_task_id", "board", type_="foreignkey")
    op.drop_column("board", "parent_task_id")
