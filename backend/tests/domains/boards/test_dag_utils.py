"""Unit tests for DAG validation utilities."""

from __future__ import annotations

import pytest

from app.domains.boards.dag_utils import (
    CyclicDependencyError,
    GoalNodeValidationError,
    validate_dag,
    validate_goal_node,
)

# ── validate_dag ─────────────────────────────────────────


def test_validate_dag_valid_linear() -> None:
    """A simple linear chain is a valid DAG."""
    task_ids = ["t1", "t2", "t3"]
    edges = [("t1", "t2"), ("t2", "t3")]
    result = validate_dag(task_ids, edges)
    assert set(result) == set(task_ids)
    # t1 must come before t2, t2 before t3
    assert result.index("t1") < result.index("t2")
    assert result.index("t2") < result.index("t3")


def test_validate_dag_valid_diamond() -> None:
    """A diamond-shaped DAG (parallel paths converging) is valid."""
    task_ids = ["t1", "t2", "t3", "t4"]
    edges = [("t1", "t2"), ("t1", "t3"), ("t2", "t4"), ("t3", "t4")]
    result = validate_dag(task_ids, edges)
    assert set(result) == set(task_ids)
    assert result.index("t1") < result.index("t2")
    assert result.index("t1") < result.index("t3")
    assert result.index("t2") < result.index("t4")
    assert result.index("t3") < result.index("t4")


def test_validate_dag_valid_no_edges() -> None:
    """Disconnected tasks with no edges are a valid (trivial) DAG."""
    task_ids = ["t1", "t2", "t3"]
    edges: list[tuple[str, str]] = []
    result = validate_dag(task_ids, edges)
    assert set(result) == set(task_ids)


def test_validate_dag_self_dependency() -> None:
    """A self-dependency raises CyclicDependencyError."""
    task_ids = ["t1", "t2"]
    edges = [("t1", "t1")]
    with pytest.raises(CyclicDependencyError, match="self-dependency"):
        validate_dag(task_ids, edges)


def test_validate_dag_simple_cycle() -> None:
    """A simple two-node cycle raises CyclicDependencyError."""
    task_ids = ["t1", "t2"]
    edges = [("t1", "t2"), ("t2", "t1")]
    with pytest.raises(CyclicDependencyError, match="cycle"):
        validate_dag(task_ids, edges)


def test_validate_dag_longer_cycle() -> None:
    """A three-node cycle raises CyclicDependencyError."""
    task_ids = ["t1", "t2", "t3"]
    edges = [("t1", "t2"), ("t2", "t3"), ("t3", "t1")]
    with pytest.raises(CyclicDependencyError, match="cycle"):
        validate_dag(task_ids, edges)


def test_validate_dag_single_task() -> None:
    """A single task with no edges is valid."""
    result = validate_dag(["t1"], [])
    assert result == ["t1"]


# ── validate_goal_node ───────────────────────────────────


def test_validate_goal_node_valid() -> None:
    """A single goal node that is a sink (nothing depends on it) is valid."""
    task_ids = ["t1", "t2", "t3"]
    goal_flags = {"t1": False, "t2": False, "t3": True}
    edges = [("t1", "t3"), ("t2", "t3")]
    validate_goal_node(task_ids, goal_flags, edges)  # Should not raise


def test_validate_goal_node_no_goal() -> None:
    """No goal node raises GoalNodeValidationError."""
    task_ids = ["t1", "t2"]
    goal_flags = {"t1": False, "t2": False}
    edges = [("t1", "t2")]
    with pytest.raises(GoalNodeValidationError, match="exactly one"):
        validate_goal_node(task_ids, goal_flags, edges)


def test_validate_goal_node_multiple_goals() -> None:
    """Multiple goal nodes raises GoalNodeValidationError."""
    task_ids = ["t1", "t2", "t3"]
    goal_flags = {"t1": False, "t2": True, "t3": True}
    edges = [("t1", "t2"), ("t1", "t3")]
    with pytest.raises(GoalNodeValidationError, match="exactly one"):
        validate_goal_node(task_ids, goal_flags, edges)


def test_validate_goal_node_with_dependents() -> None:
    """A goal node that has dependents (is not a sink) raises GoalNodeValidationError."""  # noqa: E501
    task_ids = ["t1", "t2", "t3"]
    goal_flags = {"t1": False, "t2": True, "t3": False}
    # t2 is goal but t3 depends on t2 -- goal is not a sink
    edges = [("t1", "t2"), ("t2", "t3")]
    with pytest.raises(GoalNodeValidationError, match="final task"):
        validate_goal_node(task_ids, goal_flags, edges)


def test_validate_goal_node_goal_has_dependencies() -> None:
    """A goal node can have dependencies (edges TO it). Only edges FROM it are forbidden."""  # noqa: E501
    task_ids = ["t1", "t2", "t3"]
    goal_flags = {"t1": False, "t2": False, "t3": True}
    # t3 is goal and depends on t1 and t2 -- this is valid
    edges = [("t1", "t3"), ("t2", "t3")]
    validate_goal_node(task_ids, goal_flags, edges)  # Should not raise
