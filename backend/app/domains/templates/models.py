"""SQLModel definitions for the board-templates domain."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlmodel import Field, Relationship, SQLModel


class TemplateCategory(SQLModel, table=True):
    """System-managed category for organizing board templates."""

    __tablename__ = "template_category"  # pyright: ignore[reportAssignmentType]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    name: str = Field(sa_column=Column(String(100), nullable=False, unique=True))
    slug: str = Field(sa_column=Column(String(100), nullable=False, unique=True))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    icon: str | None = Field(
        default=None, sa_column=Column(String(50), nullable=True)
    )
    display_order: int = Field(
        default=0, sa_column=Column(Integer, nullable=False, server_default="0")
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    templates: list[BoardTemplate] = Relationship(back_populates="category")


class BoardTemplate(SQLModel, table=True):
    """A reusable board blueprint saved from an existing board."""

    __tablename__ = "board_template"  # pyright: ignore[reportAssignmentType]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    user_id: str = Field(foreign_key="user.id", index=True)
    category_id: str | None = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("template_category.id"),
            nullable=True,
            index=True,
        ),
    )
    title: str = Field(sa_column=Column(String(200), nullable=False))
    description: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    visibility: str = Field(
        default="private",
        sa_column=Column(String(20), nullable=False, server_default="private"),
    )
    source_board_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    task_count: int = Field(
        default=0, sa_column=Column(Integer, nullable=False, server_default="0")
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    category: TemplateCategory | None = Relationship(back_populates="templates")
    tasks: list[TemplateTask] = Relationship(
        back_populates="template",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )
    dependencies: list[TemplateTaskDependency] = Relationship(
        back_populates="template",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )


class TemplateTask(SQLModel, table=True):
    """A task within a board template."""

    __tablename__ = "template_task"  # pyright: ignore[reportAssignmentType]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    template_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("board_template.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    title: str = Field(default="")
    description: str = Field(
        default="", sa_column=Column(Text, nullable=False, server_default="")
    )
    is_goal_node: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    priority: str | None = Field(default=None)
    estimated_minutes: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    template: BoardTemplate = Relationship(back_populates="tasks")
    subtasks: list[TemplateSubtask] = Relationship(
        back_populates="template_task",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "TemplateSubtask.position",
            "lazy": "selectin",
        },
    )


class TemplateTaskDependency(SQLModel, table=True):
    """A directed edge in the template's DAG structure."""

    __tablename__ = "template_task_dependency"  # pyright: ignore[reportAssignmentType]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    template_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("board_template.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    dependent_task_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("template_task.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    dependency_task_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("template_task.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    template: BoardTemplate = Relationship(back_populates="dependencies")

    __table_args__ = (
        UniqueConstraint(
            "dependent_task_id",
            "dependency_task_id",
            name="uq_template_task_dependency_pair",
        ),
    )


class TemplateSubtask(SQLModel, table=True):
    """A subtask within a template task."""

    __tablename__ = "template_subtask"  # pyright: ignore[reportAssignmentType]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    template_task_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("template_task.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    title: str = Field(default="")
    position: str = Field(default="a0", sa_column=Column(String(50), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    template_task: TemplateTask = Relationship(back_populates="subtasks")
