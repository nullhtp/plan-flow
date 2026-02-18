"""Board-level operations: CRUD, listing, and response building."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.board_repository import BoardRepository
from app.domains.boards.models import Board
from app.domains.boards.ownership import (
    BoardNotFoundError,
    validate_board_ownership,
)
from app.domains.boards.schemas import BoardResponse, EdgeResponse, TaskResponse
from app.domains.goals.models import Goal

# ── Board CRUD ──────────────────────────────────────────


async def list_boards(
    session: AsyncSession,
    user_id: str,
) -> list[dict[str, Any]]:
    """Return all boards for a user with summary stats."""
    repo = BoardRepository(session)
    return await repo.list_by_user(user_id)


async def get_board(
    session: AsyncSession,
    board_id: str,
    user_id: str,
) -> Board:
    """Retrieve a board with nested data, validating ownership."""
    repo = BoardRepository(session)
    board = await repo.get_with_relations(board_id)

    if board is None:
        raise BoardNotFoundError

    # Validate ownership via goal
    goal = await session.get(Goal, board.goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError

    return board


async def get_board_by_goal(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
) -> Board:
    """Retrieve a board by goal_id, validating ownership."""
    goal = await session.get(Goal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise BoardNotFoundError

    repo = BoardRepository(session)
    board = await repo.get_with_relations_by_goal(goal_id)

    if board is None:
        raise BoardNotFoundError

    return board


async def update_board(
    session: AsyncSession,
    board_id: str,
    user_id: str,
    title: str,
) -> Board:
    """Update board title."""
    board = await validate_board_ownership(session, board_id, user_id)
    board.title = title
    board.updated_at = datetime.now(UTC)
    repo = BoardRepository(session)
    await repo.update(board)
    await session.commit()
    return await get_board(session, board_id, user_id)


async def get_user_meta_for_board(
    session: AsyncSession,
    board: Board,
) -> dict[str, Any] | None:
    """Read user_meta from the board's related goal's ai_context."""
    goal = await session.get(Goal, board.goal_id)
    if goal is None:
        return None
    ai_context: dict[str, Any] = dict(goal.ai_context) if goal.ai_context else {}
    return ai_context.get("user_meta")


# ── Response Building ────────────────────────────────────


def build_board_response(
    board: Board, user_meta: dict[str, Any] | None = None
) -> BoardResponse:
    """Build a BoardResponse from a Board with loaded relationships."""
    tasks = board.tasks
    edges: list[EdgeResponse] = []
    task_responses: list[TaskResponse] = []

    # Collect all dependency info
    for task in tasks:
        dependency_ids = [d.dependency_task_id for d in task.dependencies]
        dependent_ids = [d.dependent_task_id for d in task.dependents]

        # Compute is_locked: at least one dependency is not done
        is_locked = False
        for dep_edge in task.dependencies:
            for t in tasks:
                if t.id == dep_edge.dependency_task_id and t.status != "done":
                    is_locked = True
                    break
            if is_locked:
                break

        task_responses.append(
            TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                is_goal_node=task.is_goal_node,
                due_date=task.due_date,
                priority=task.priority,
                estimated_minutes=task.estimated_minutes,
                subtasks=[
                    {  # type: ignore[misc]
                        "id": s.id,
                        "title": s.title,
                        "completed": s.completed,
                        "position": s.position,
                        "action_label": s.action_label,
                        "action_icon": s.action_icon,
                        "action_prompt": s.action_prompt,
                        "created_at": s.created_at,
                    }
                    for s in task.subtasks
                ],
                dependency_ids=dependency_ids,
                dependent_ids=dependent_ids,
                is_locked=is_locked,
                created_at=task.created_at,
            )
        )

        # Add edges
        for dep_edge in task.dependencies:
            edges.append(
                EdgeResponse(
                    source=dep_edge.dependency_task_id,
                    target=dep_edge.dependent_task_id,
                )
            )

    # Deduplicate edges (they may appear from both sides)
    seen_edges: set[tuple[str, str]] = set()
    unique_edges: list[EdgeResponse] = []
    for edge in edges:
        key = (edge.source, edge.target)
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(edge)

    # Compute is_completed: goal node has status done
    is_completed = any(t.is_goal_node and t.status == "done" for t in tasks)

    return BoardResponse(
        id=board.id,
        goal_id=board.goal_id,
        title=board.title,
        tasks=task_responses,
        edges=unique_edges,
        is_completed=is_completed,
        user_meta=user_meta,
        created_at=board.created_at,
    )


def format_qa_pairs(ai_context: dict[str, Any]) -> str:
    """Format questions and answers from ai_context into a string for the prompt."""
    lines: list[str] = []
    questions = ai_context.get("questions", [])
    answers = ai_context.get("answers", {})
    follow_up_questions = ai_context.get("follow_up_questions", [])
    follow_up_answers = ai_context.get("follow_up_answers", {})

    for q in questions:
        qid = q.get("id", "")
        text = q.get("text", "")
        answer = answers.get(qid, "(not answered)")
        lines.append(f"Q ({qid}): {text}\nA: {answer}")

    for q in follow_up_questions:
        qid = q.get("id", "")
        text = q.get("text", "")
        answer = follow_up_answers.get(qid, "(not answered)")
        lines.append(f"Q ({qid}): {text}\nA: {answer}")

    return "\n\n".join(lines)
