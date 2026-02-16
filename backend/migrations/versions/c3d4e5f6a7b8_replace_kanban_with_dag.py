"""replace_kanban_with_dag

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-16 16:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop kanban tables and recreate with DAG schema."""
    # Drop existing tables in dependency order
    op.drop_index(op.f("ix_subtask_task_id"), table_name="subtask")
    op.drop_table("subtask")
    op.drop_index(op.f("ix_task_column_id"), table_name="task")
    op.drop_table("task")
    op.drop_index(op.f("ix_board_column_board_id"), table_name="board_column")
    op.drop_table("board_column")
    op.drop_index(op.f("ix_board_goal_id"), table_name="board")
    op.drop_table("board")

    # Recreate board table (same schema)
    op.create_table(
        "board",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("goal_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goal.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", name="uq_board_goal_id"),
    )
    op.create_index(op.f("ix_board_goal_id"), "board", ["goal_id"], unique=True)

    # Create task table with board_id FK (no column_id), status, is_goal_node
    op.create_table(
        "task",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("board_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "status", sa.String(20), server_default="not_started", nullable=False
        ),
        sa.Column("is_goal_node", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["board.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_board_id"), "task", ["board_id"], unique=False)

    # Create task_dependency junction table
    op.create_table(
        "task_dependency",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "dependent_task_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "dependency_task_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dependent_task_id"], ["task.id"]),
        sa.ForeignKeyConstraint(["dependency_task_id"], ["task.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dependent_task_id", "dependency_task_id", name="uq_task_dependency_pair"
        ),
    )
    op.create_index(
        op.f("ix_task_dependency_dependent_task_id"),
        "task_dependency",
        ["dependent_task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_dependency_dependency_task_id"),
        "task_dependency",
        ["dependency_task_id"],
        unique=False,
    )

    # Recreate subtask table
    op.create_table(
        "subtask",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("task_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("position", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subtask_task_id"), "subtask", ["task_id"], unique=False)


def downgrade() -> None:
    """Revert to kanban schema."""
    # Drop new tables
    op.drop_index(op.f("ix_subtask_task_id"), table_name="subtask")
    op.drop_table("subtask")
    op.drop_index(
        op.f("ix_task_dependency_dependency_task_id"), table_name="task_dependency"
    )
    op.drop_index(
        op.f("ix_task_dependency_dependent_task_id"), table_name="task_dependency"
    )
    op.drop_table("task_dependency")
    op.drop_index(op.f("ix_task_board_id"), table_name="task")
    op.drop_table("task")
    op.drop_index(op.f("ix_board_goal_id"), table_name="board")
    op.drop_table("board")

    # Recreate old kanban tables
    op.create_table(
        "board",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("goal_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goal.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", name="uq_board_goal_id"),
    )
    op.create_index(op.f("ix_board_goal_id"), "board", ["goal_id"], unique=True)

    op.create_table(
        "board_column",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("board_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("position", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["board_id"], ["board.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_board_column_board_id"), "board_column", ["board_id"], unique=False
    )

    op.create_table(
        "task",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("column_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("position", sa.String(50), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["column_id"], ["board_column.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_column_id"), "task", ["column_id"], unique=False)

    op.create_table(
        "subtask",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("task_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("position", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subtask_task_id"), "subtask", ["task_id"], unique=False)
