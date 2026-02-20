"""Backward-compatibility shim.

All logic has moved to board_service.py, task_service.py, and subtask_service.py.
This module re-exports names so existing consumers don't break during the
transition period. These re-exports will be removed in Phase 4.
"""

from __future__ import annotations

# ── Re-exports from board_service ────────────────────────
from app.domains.boards.board_service import (  # noqa: F401
    build_board_response,
    format_qa_pairs,
    get_board,
    get_board_by_goal,
    get_user_meta_for_board,
    list_boards,
    update_board,
)

# ── Re-exports from ownership ────────────────────────────
from app.domains.boards.ownership import (  # noqa: F401
    BoardNotFoundError,
    SubtaskNotFoundError,
    TaskNotFoundError,
    validate_board_ownership,
    validate_subtask_ownership,
    validate_task_ownership,
)

# ── Re-exports from position_utils ───────────────────────
from app.domains.boards.position_utils import (  # noqa: F401
    generate_position_after,
    generate_position_between,
)

# ── Re-exports from subtask_service ──────────────────────
from app.domains.boards.subtask_service import (  # noqa: F401
    create_subtask,
    delete_subtask,
    update_subtask,
)

# ── Re-exports from task_service ─────────────────────────
from app.domains.boards.task_service import (  # noqa: F401
    BoardAlreadyExistsError,
    BoardGenerationError,
    DependencyError,
    GoalNotReadyError,
    TaskStatusError,
    are_dependencies_met,
    create_board_from_skeleton,
    create_task,
    delete_task,
    get_task_dependencies,
    get_task_dependents,
    update_task,
    update_task_with_enrichment,
    validate_goal_for_generation,
)

# ── Re-exports from goal transitions (now in goals/service) ──
from app.domains.goals.service import (  # noqa: F401
    revert_goal_to_answered,
    revert_goal_to_questioning,
    transition_goal_to_active,
    transition_goal_to_generating,
)

# Private aliases for callers that used the underscore-prefixed names
_build_board_response = build_board_response
_format_qa_pairs = format_qa_pairs
_validate_board_ownership = validate_board_ownership
_validate_task_ownership = validate_task_ownership
_validate_subtask_ownership = validate_subtask_ownership
