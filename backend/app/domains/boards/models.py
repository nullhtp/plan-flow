import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlmodel import Field, Relationship, SQLModel


class Board(SQLModel, table=True):
    """A DAG-based task board generated from a goal by the AI pipeline.

    Root boards have goal_id set and parent_task_id null.
    Sub-boards have parent_task_id set and goal_id null.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    goal_id: str | None = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("goal.id"),
            nullable=True,
            unique=True,
            index=True,
        ),
    )
    parent_task_id: str | None = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("task.id", ondelete="CASCADE"),
            nullable=True,
            unique=True,
            index=True,
        ),
    )
    title: str = Field(default="")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    tasks: list["Task"] = Relationship(
        back_populates="board",
        sa_relationship_kwargs={
            "foreign_keys": "Task.board_id",
            "order_by": "Task.created_at",
            "lazy": "selectin",
        },
    )
    parent_task: Optional["Task"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "Board.parent_task_id",
            "lazy": "selectin",
            "uselist": False,
        },
    )

    __table_args__ = (
        UniqueConstraint("goal_id", name="uq_board_goal_id"),
        CheckConstraint(
            "goal_id IS NOT NULL OR parent_task_id IS NOT NULL",
            name="ck_board_goal_or_parent_task",
        ),
    )


class Task(SQLModel, table=True):
    """A task within a board, part of a DAG structure."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    board_id: str = Field(foreign_key="board.id", index=True)
    title: str = Field(default="")
    description: str = Field(
        default="", sa_column=Column(Text, nullable=False, server_default="")
    )
    status: str = Field(
        default="not_started",
        sa_column=Column(String(20), nullable=False, server_default="not_started"),
    )
    is_goal_node: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    due_date: datetime | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
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
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    board: "Board" = Relationship(
        back_populates="tasks",
        sa_relationship_kwargs={
            "foreign_keys": "Task.board_id",
        },
    )
    subtasks: list["Subtask"] = Relationship(
        back_populates="task",
        sa_relationship_kwargs={"order_by": "Subtask.position", "lazy": "selectin"},
    )
    # Dependencies: tasks that this task depends on (prerequisites)
    dependencies: list["TaskDependency"] = Relationship(
        back_populates="dependent_task",
        sa_relationship_kwargs={
            "foreign_keys": "TaskDependency.dependent_task_id",
            "lazy": "selectin",
        },
    )
    # Dependents: tasks that depend on this task
    dependents: list["TaskDependency"] = Relationship(
        back_populates="dependency_task",
        sa_relationship_kwargs={
            "foreign_keys": "TaskDependency.dependency_task_id",
            "lazy": "selectin",
        },
    )
    # Sub-board: optional board that decomposes this task into a full DAG
    sub_board: Optional["Board"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "Board.parent_task_id",
            "uselist": False,
            "lazy": "selectin",
        },
    )


class TaskDependency(SQLModel, table=True):
    """A directed edge in the task DAG: dependent_task depends on dependency_task."""

    __tablename__ = "task_dependency"  # pyright: ignore[reportAssignmentType]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    dependent_task_id: str = Field(foreign_key="task.id", index=True)
    dependency_task_id: str = Field(foreign_key="task.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    dependent_task: "Task" = Relationship(
        back_populates="dependencies",
        sa_relationship_kwargs={"foreign_keys": "TaskDependency.dependent_task_id"},
    )
    dependency_task: "Task" = Relationship(
        back_populates="dependents",
        sa_relationship_kwargs={"foreign_keys": "TaskDependency.dependency_task_id"},
    )

    __table_args__ = (
        UniqueConstraint(
            "dependent_task_id",
            "dependency_task_id",
            name="uq_task_dependency_pair",
        ),
    )


class Subtask(SQLModel, table=True):
    """A checklist item within a task."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    task_id: str = Field(foreign_key="task.id", index=True)
    title: str = Field(default="")
    completed: bool = Field(
        default=False, sa_column=Column(Boolean, nullable=False, server_default="false")
    )
    position: str = Field(default="a0", sa_column=Column(String(50), nullable=False))
    action_label: str | None = Field(
        default=None,
        sa_column=Column(String(60), nullable=True),
    )
    action_icon: str | None = Field(
        default=None,
        sa_column=Column(String(20), nullable=True),
    )
    action_prompt: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    task: "Task" = Relationship(back_populates="subtasks")


class Artifact(SQLModel, table=True):
    """Persistent content generated by AI for a task (e.g., agreements, plans)."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    task_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("task.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    title: str = Field(max_length=200)
    content: str = Field(
        default="", sa_column=Column(Text, nullable=False, server_default="")
    )
    content_type: str = Field(
        default="text/markdown",
        sa_column=Column(String(50), nullable=False, server_default="text/markdown"),
    )
    created_by: str = Field(
        default="ai",
        sa_column=Column(String(20), nullable=False, server_default="ai"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
