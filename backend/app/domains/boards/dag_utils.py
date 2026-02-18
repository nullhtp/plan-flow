"""DAG validation utilities for task dependency graphs.

Uses Kahn's algorithm (BFS topological sort) for cycle detection.
"""

from __future__ import annotations

from collections import defaultdict, deque


class CyclicDependencyError(Exception):
    """Raised when a dependency graph contains a cycle."""


class GoalNodeValidationError(Exception):
    """Raised when goal node constraints are violated."""


class NestingDepthError(Exception):
    """Raised when sub-board nesting would exceed the 1-level limit."""


def validate_dag(
    task_ids: list[str],
    edges: list[tuple[str, str]],
) -> list[str]:
    """Validate that tasks and edges form a valid DAG.

    Args:
        task_ids: List of task identifiers.
        edges: List of (dependency_task_id, dependent_task_id) tuples.
            Each edge means dependent_task depends on dependency_task.

    Returns:
        Topologically sorted list of task IDs.

    Raises:
        CyclicDependencyError: If the graph contains a cycle (including self-deps).
    """
    task_set = set(task_ids)

    # Check for self-dependencies
    for dep, dependent in edges:
        if dep == dependent:
            raise CyclicDependencyError(
                f"Task '{dep}' depends on itself (self-dependency)"
            )

    # Build adjacency list and in-degree map
    # Edge direction: dependency -> dependent (prerequisite points to blocked task)
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {tid: 0 for tid in task_set}

    for dep, dependent in edges:
        adj[dep].append(dependent)
        in_degree[dependent] = in_degree.get(dependent, 0) + 1

    # Kahn's algorithm
    queue: deque[str] = deque()
    for tid in task_ids:
        if in_degree[tid] == 0:
            queue.append(tid)

    sorted_order: list[str] = []
    while queue:
        node = queue.popleft()
        sorted_order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_order) != len(task_set):
        # Find tasks involved in cycles
        cycle_tasks = [tid for tid in task_ids if tid not in set(sorted_order)]
        raise CyclicDependencyError(
            f"Dependency graph contains a cycle involving tasks: {cycle_tasks}"
        )

    return sorted_order


def validate_goal_node(
    task_ids: list[str],
    goal_flags: dict[str, bool],
    edges: list[tuple[str, str]],
) -> None:
    """Validate goal node constraints.

    Args:
        task_ids: List of task identifiers.
        goal_flags: Mapping of task_id -> is_goal_node.
        edges: List of (dependency_task_id, dependent_task_id) tuples.

    Raises:
        GoalNodeValidationError: If constraints are violated.
    """
    goal_nodes = [tid for tid in task_ids if goal_flags.get(tid, False)]

    if len(goal_nodes) == 0:
        raise GoalNodeValidationError("Board must have exactly one goal node")

    if len(goal_nodes) > 1:
        raise GoalNodeValidationError(
            f"Board must have exactly one goal node, found {len(goal_nodes)}"
        )

    goal_id = goal_nodes[0]

    # Check goal node has no dependents (nothing depends on it)
    for _, dependent in edges:
        if dependent != goal_id:
            continue
        # This edge goes TO the goal node, that's fine (it's a dependency OF the goal)
    for dep, _ in edges:
        if dep == goal_id:
            raise GoalNodeValidationError(
                "Goal node must be the final task (nothing should depend on it)"
            )


def is_root_board(board: object) -> bool:
    """Check whether a board is a root board (not a sub-board).

    Args:
        board: A Board instance (uses duck typing to avoid import cycles).

    Returns:
        True if the board has no parent_task_id (i.e., is a root board).
    """
    return getattr(board, "parent_task_id", None) is None


def validate_nesting_depth(board: object) -> None:
    """Validate that sub-board creation is allowed for tasks on this board.

    Sub-boards are limited to 1 level deep. Tasks on sub-boards cannot
    themselves have sub-boards.

    Args:
        board: The board the task belongs to.

    Raises:
        NestingDepthError: If the board is already a sub-board.
    """
    if not is_root_board(board):
        raise NestingDepthError(
            "Sub-boards cannot be nested beyond 1 level. "
            "Tasks on sub-boards cannot themselves have sub-boards."
        )
