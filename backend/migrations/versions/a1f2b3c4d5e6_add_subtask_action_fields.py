"""add_subtask_action_fields

Revision ID: a1f2b3c4d5e6
Revises: eb35d52da786
Create Date: 2026-02-18 14:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1f2b3c4d5e6"
down_revision = "eb35d52da786"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subtask", sa.Column("action_label", sa.String(60), nullable=True))
    op.add_column("subtask", sa.Column("action_icon", sa.String(20), nullable=True))
    op.add_column("subtask", sa.Column("action_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("subtask", "action_prompt")
    op.drop_column("subtask", "action_icon")
    op.drop_column("subtask", "action_label")
