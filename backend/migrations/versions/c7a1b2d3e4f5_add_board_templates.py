"""add_board_templates

Revision ID: c7a1b2d3e4f5
Revises: 083ac4d21c2f
Create Date: 2026-03-07 12:00:00.000000

"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7a1b2d3e4f5"
down_revision = "083ac4d21c2f"
branch_labels = None
depends_on = None

# Seed categories: (name, slug, description, icon, display_order)
SEED_CATEGORIES = [
    ("Career", "career", "Career growth and job-related goals", "briefcase", 1),
    ("Travel", "travel", "Travel planning and relocation", "plane", 2),
    (
        "Health & Fitness",
        "health-fitness",
        "Health, fitness, and wellness goals",
        "heart",
        3,
    ),
    ("Education", "education", "Learning and skill development", "graduation-cap", 4),
    ("Finance", "finance", "Financial planning and budgeting", "wallet", 5),
    ("Home & Living", "home-living", "Home improvement and lifestyle", "home", 6),
    ("Projects", "projects", "Side projects and creative work", "rocket", 7),
    ("Events", "events", "Event planning and organization", "calendar", 8),
    (
        "Personal Development",
        "personal-development",
        "Self-improvement and habits",
        "star",
        9,
    ),
    ("Other", "other", "Miscellaneous goals", "folder", 10),
]


def upgrade() -> None:
    # template_category
    op.create_table(
        "template_category",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_template_category_name"),
        sa.UniqueConstraint("slug", name="uq_template_category_slug"),
    )

    # board_template
    op.create_table(
        "board_template",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("category_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "visibility",
            sa.String(20),
            nullable=False,
            server_default="private",
        ),
        sa.Column("source_board_id", sa.String(), nullable=True),
        sa.Column("task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["template_category.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_board_template_user_id", "board_template", ["user_id"])
    op.create_index("ix_board_template_category_id", "board_template", ["category_id"])
    op.create_index("ix_board_template_visibility", "board_template", ["visibility"])

    # template_task
    op.create_table(
        "template_task",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_goal_node", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"], ["board_template.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_template_task_template_id", "template_task", ["template_id"])

    # template_task_dependency
    op.create_table(
        "template_task_dependency",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("dependent_task_id", sa.String(), nullable=False),
        sa.Column("dependency_task_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"], ["board_template.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["dependent_task_id"], ["template_task.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["dependency_task_id"], ["template_task.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dependent_task_id",
            "dependency_task_id",
            name="uq_template_task_dependency_pair",
        ),
    )
    op.create_index(
        "ix_template_task_dependency_template_id",
        "template_task_dependency",
        ["template_id"],
    )

    # template_subtask
    op.create_table(
        "template_subtask",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("template_task_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("position", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_task_id"], ["template_task.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_template_subtask_template_task_id",
        "template_subtask",
        ["template_task_id"],
    )

    # Seed categories
    template_category = sa.table(
        "template_category",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("icon", sa.String),
        sa.column("display_order", sa.Integer),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        template_category,
        [
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slug,
                "description": desc,
                "icon": icon,
                "display_order": order,
                "created_at": now,
            }
            for name, slug, desc, icon, order in SEED_CATEGORIES
        ],
    )


def downgrade() -> None:
    op.drop_table("template_subtask")
    op.drop_table("template_task_dependency")
    op.drop_table("template_task")
    op.drop_table("board_template")
    op.drop_table("template_category")
