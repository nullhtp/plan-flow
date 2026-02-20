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
from app.domains.boards.schemas import (
    BoardResponse,
    EdgeResponse,
    ParentBoardResponse,
    SubBoardProgressResponse,
    TaskResponse,
)
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
    """Retrieve a board with nested data, validating ownership.

    Supports both root boards (ownership via goal) and sub-boards
    (ownership traced via parent_task -> parent_board -> goal).
    """
    repo = BoardRepository(session)
    board = await repo.get_with_relations(board_id)

    if board is None:
        raise BoardNotFoundError

    # Validate ownership: root boards check goal directly,
    # sub-boards trace parent_task -> board -> goal
    await _validate_board_ownership_chain(session, board, user_id)

    return board


async def _validate_board_ownership_chain(
    session: AsyncSession, board: Board, user_id: str
) -> None:
    """Validate ownership for both root boards and sub-boards.

    Root boards: board -> goal -> user
    Sub-boards: board -> parent_task -> parent_board -> goal -> user
    """
    if board.goal_id is not None:
        # Root board: check goal ownership directly
        goal = await session.get(Goal, board.goal_id)
        if goal is None or goal.user_id != user_id:
            raise BoardNotFoundError
    elif board.parent_task_id is not None:
        # Sub-board: trace to root board's goal
        from app.domains.boards.models import Task

        parent_task = await session.get(Task, board.parent_task_id)
        if parent_task is None:
            raise BoardNotFoundError
        parent_board = await session.get(Board, parent_task.board_id)
        if parent_board is None:
            raise BoardNotFoundError
        # Recurse (handles multi-level if ever needed, but currently 1-level only)
        await _validate_board_ownership_chain(session, parent_board, user_id)
    else:
        raise BoardNotFoundError


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
    """Read user_meta from the board's related goal's ai_context.

    For sub-boards, traces to the root board's goal.
    """
    goal_id = board.goal_id
    if goal_id is None and board.parent_task_id is not None:
        # Sub-board: trace to root board's goal
        repo = BoardRepository(session)
        parent_board = await repo.get_parent_board(board)
        if parent_board is not None:
            goal_id = parent_board.goal_id
    if goal_id is None:
        return None
    goal = await session.get(Goal, goal_id)
    if goal is None:
        return None
    ai_context: dict[str, Any] = dict(goal.ai_context) if goal.ai_context else {}
    return ai_context.get("user_meta")


# ── Response Building ────────────────────────────────────


def build_board_response(
    board: Board,
    user_meta: dict[str, Any] | None = None,
    parent_board: Board | None = None,
) -> BoardResponse:
    """Build a BoardResponse from a Board with loaded relationships.

    Args:
        board: The board with tasks and edges loaded.
        user_meta: Optional user metadata from goal's ai_context.
        parent_board: Optional parent board for breadcrumb navigation (sub-boards only).
    """
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

        # Compute sub-board info for this task.
        # Check the instance __dict__ to avoid triggering a lazy load
        # in async context (MissingGreenlet error).
        sub_board_id: str | None = None
        sub_board_progress: SubBoardProgressResponse | None = None
        sub_board = task.__dict__.get("sub_board")
        if sub_board is not None:
            sub_board_id = sub_board.id
            sb_tasks = sub_board.__dict__.get("tasks", [])
            sub_board_progress = SubBoardProgressResponse(
                task_count=len(sb_tasks),
                completed_task_count=sum(1 for t in sb_tasks if t.status == "done"),
            )

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
                sub_board_id=sub_board_id,
                sub_board_progress=sub_board_progress,
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

    # Build parent_board reference for breadcrumb navigation
    parent_board_ref: ParentBoardResponse | None = None
    if parent_board is not None:
        parent_board_ref = ParentBoardResponse(
            id=parent_board.id,
            title=parent_board.title,
        )

    return BoardResponse(
        id=board.id,
        goal_id=board.goal_id,
        title=board.title,
        tasks=task_responses,
        edges=unique_edges,
        is_completed=is_completed,
        user_meta=user_meta,
        parent_task_id=board.parent_task_id,
        parent_board=parent_board_ref,
        created_at=board.created_at,
    )


def format_qa_pairs(ai_context: dict[str, Any]) -> str:
    """Format questions and answers from ai_context into a string for the prompt.

    Supports both the new rounds-based format and the legacy flat format.
    """
    lines: list[str] = []

    # New rounds-based format
    rounds = ai_context.get("rounds")
    if rounds:
        for r in rounds:
            questions = r.get("questions", [])
            answers = r.get("answers", {})
            for q in questions:
                qid = q.get("id", "")
                text = q.get("text", "")
                answer = answers.get(qid, "(not answered)")
                lines.append(f"Q ({qid}): {text}\nA: {answer}")
        return "\n\n".join(lines)

    # Legacy flat format (backward compat)
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
