"""fractional_positions_and_subtasks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-16 15:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _int_to_fractional(n: int) -> str:
    """Convert an integer position to a fractional index string.

    Produces lexicographically sortable strings: 0->"a0", 1->"a1", ..., 9->"a9",
    10->"aA", etc.  This is consistent with the `fractional-indexing` library format.
    """
    # Use simple zero-padded hex-ish encoding for small numbers
    # a0, a1, ..., a9, aA, aB, ..., aZ, aa, ab, ...
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if n < len(digits):
        return f"a{digits[n]}"
    # For larger numbers, just use "a" + zero-padded string
    return f"b{n:04d}"


def upgrade() -> None:
    """Convert integer positions to fractional index strings and add subtask table."""

    # 1. Convert board_column.position from integer to varchar(50)
    # First add a temporary column
    op.add_column(
        "board_column",
        sa.Column("position_new", sa.String(50), nullable=True),
    )
    # Migrate data: convert integer positions to fractional index strings
    conn = op.get_bind()
    columns = conn.execute(
        sa.text("SELECT id, position FROM board_column ORDER BY position")
    )
    for row in columns:
        frac = _int_to_fractional(row[1])
        conn.execute(
            sa.text("UPDATE board_column SET position_new = :pos WHERE id = :id"),
            {"pos": frac, "id": row[0]},
        )
    # Set default for any nulls
    conn.execute(
        sa.text(
            "UPDATE board_column SET position_new = 'a0' WHERE position_new IS NULL"
        )
    )
    # Drop old column and rename new one
    op.drop_column("board_column", "position")
    op.alter_column(
        "board_column", "position_new", new_column_name="position", nullable=False
    )

    # 2. Convert task.position from integer to varchar(50)
    op.add_column(
        "task",
        sa.Column("position_new", sa.String(50), nullable=True),
    )
    tasks = conn.execute(sa.text("SELECT id, position FROM task ORDER BY position"))
    for row in tasks:
        frac = _int_to_fractional(row[1])
        conn.execute(
            sa.text("UPDATE task SET position_new = :pos WHERE id = :id"),
            {"pos": frac, "id": row[0]},
        )
    conn.execute(
        sa.text("UPDATE task SET position_new = 'a0' WHERE position_new IS NULL")
    )
    op.drop_column("task", "position")
    op.alter_column("task", "position_new", new_column_name="position", nullable=False)

    # 3. Create subtask table
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
    """Revert fractional positions to integers and drop subtask table."""
    # Drop subtask table
    op.drop_index(op.f("ix_subtask_task_id"), table_name="subtask")
    op.drop_table("subtask")

    conn = op.get_bind()

    # Revert task.position to integer
    op.add_column(
        "task",
        sa.Column("position_int", sa.Integer(), nullable=True),
    )
    # Assign integer positions based on lexicographic order within each column
    task_rows = conn.execute(
        sa.text("SELECT id, column_id, position FROM task ORDER BY column_id, position")
    )
    current_col = None
    pos = 0
    for row in task_rows:
        if row[1] != current_col:
            current_col = row[1]
            pos = 0
        conn.execute(
            sa.text("UPDATE task SET position_int = :pos WHERE id = :id"),
            {"pos": pos, "id": row[0]},
        )
        pos += 1
    conn.execute(sa.text("UPDATE task SET position_int = 0 WHERE position_int IS NULL"))
    op.drop_column("task", "position")
    op.alter_column("task", "position_int", new_column_name="position", nullable=False)

    # Revert board_column.position to integer
    op.add_column(
        "board_column",
        sa.Column("position_int", sa.Integer(), nullable=True),
    )
    col_rows = conn.execute(
        sa.text(
            "SELECT id, board_id, position"
            " FROM board_column ORDER BY board_id, position"
        )
    )
    current_board = None
    pos = 0
    for row in col_rows:
        if row[1] != current_board:
            current_board = row[1]
            pos = 0
        conn.execute(
            sa.text("UPDATE board_column SET position_int = :pos WHERE id = :id"),
            {"pos": pos, "id": row[0]},
        )
        pos += 1
    conn.execute(
        sa.text("UPDATE board_column SET position_int = 0 WHERE position_int IS NULL")
    )
    op.drop_column("board_column", "position")
    op.alter_column(
        "board_column", "position_int", new_column_name="position", nullable=False
    )
