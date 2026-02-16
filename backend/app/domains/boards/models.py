import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlmodel import Field, Relationship, SQLModel


class Board(SQLModel, table=True):
    """A kanban board generated from a goal by the AI pipeline."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    goal_id: str = Field(
        foreign_key="goal.id",
        index=True,
        sa_column_kwargs={"unique": True},
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

    columns: list["BoardColumn"] = Relationship(
        back_populates="board",
        sa_relationship_kwargs={"order_by": "BoardColumn.position", "lazy": "selectin"},
    )

    __table_args__ = (UniqueConstraint("goal_id", name="uq_board_goal_id"),)


class BoardColumn(SQLModel, table=True):
    """A column (phase/stage) within a kanban board."""

    __tablename__ = "board_column"  # pyright: ignore[reportAssignmentType]

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    board_id: str = Field(foreign_key="board.id", index=True)
    title: str = Field(default="")
    description: str = Field(
        default="", sa_column=Column(Text, nullable=False, server_default="")
    )
    position: str = Field(default="a0", sa_column=Column(String(50), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    board: "Board" = Relationship(back_populates="columns")
    tasks: list["Task"] = Relationship(
        back_populates="column",
        sa_relationship_kwargs={"order_by": "Task.position", "lazy": "selectin"},
    )


class Task(SQLModel, table=True):
    """A task within a board column."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    column_id: str = Field(foreign_key="board_column.id", index=True)
    title: str = Field(default="")
    description: str = Field(
        default="", sa_column=Column(Text, nullable=False, server_default="")
    )
    position: str = Field(default="a0", sa_column=Column(String(50), nullable=False))
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

    column: "BoardColumn" = Relationship(back_populates="tasks")
    subtasks: list["Subtask"] = Relationship(
        back_populates="task",
        sa_relationship_kwargs={"order_by": "Subtask.position", "lazy": "selectin"},
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    task: "Task" = Relationship(back_populates="subtasks")
