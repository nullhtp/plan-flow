"""Unit tests for fractional indexing utility functions."""

from __future__ import annotations

from app.domains.boards.service import (
    generate_position_after,
    generate_position_between,
    int_to_fractional,
)


def test_int_to_fractional_basic() -> None:
    """Converts small integers to expected fractional index strings."""
    assert int_to_fractional(0) == "a0"
    assert int_to_fractional(1) == "a1"
    assert int_to_fractional(9) == "a9"
    assert int_to_fractional(10) == "aA"


def test_int_to_fractional_ordering() -> None:
    """Fractional index strings from sequential integers sort lexicographically."""
    values = [int_to_fractional(i) for i in range(20)]
    assert values == sorted(values)


def test_generate_position_between_none_none() -> None:
    """Both None produces a valid key."""
    pos = generate_position_between(None, None)
    assert isinstance(pos, str)
    assert len(pos) > 0


def test_generate_position_after_none() -> None:
    """After None produces a valid first position."""
    pos = generate_position_after(None)
    assert isinstance(pos, str)
    assert len(pos) > 0


def test_generate_position_after_value() -> None:
    """After a value produces a position that sorts after it."""
    first = generate_position_after(None)
    second = generate_position_after(first)
    assert second > first


def test_generate_position_between_two_values() -> None:
    """Between two values produces a position between them."""
    a = "a0"
    b = "a9"
    mid = generate_position_between(a, b)
    assert a < mid < b


def test_generate_position_between_adjacent() -> None:
    """Between adjacent values produces a valid in-between position."""
    a = "a0"
    b = "a1"
    mid = generate_position_between(a, b)
    assert a < mid < b


def test_sequential_positions_maintain_order() -> None:
    """Multiple sequential appends maintain sort order."""
    positions = []
    last = None
    for _ in range(20):
        pos = generate_position_after(last)
        positions.append(pos)
        last = pos
    assert positions == sorted(positions)


def test_interleaved_insertions_maintain_order() -> None:
    """Inserting between existing positions maintains sort order."""
    a = generate_position_after(None)
    b = generate_position_after(a)
    c = generate_position_after(b)

    # Insert between a and b
    ab = generate_position_between(a, b)
    # Insert between b and c
    bc = generate_position_between(b, c)

    all_positions = [a, ab, b, bc, c]
    assert all_positions == sorted(all_positions)


def test_generate_position_before() -> None:
    """Before a value (None, value) produces a position before it."""
    existing = "a5"
    before = generate_position_between(None, existing)
    assert before < existing
