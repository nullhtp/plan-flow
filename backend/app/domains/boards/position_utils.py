"""Fractional indexing utilities for ordered positioning.

Generates lexicographically-sortable string keys that allow inserting items
between two existing keys without renumbering, matching the JS
``fractional-indexing`` library's character set.
"""

from __future__ import annotations

# Character set for fractional index keys
# (matches the JS `fractional-indexing` library).
_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE = len(_DIGITS)


def _midpoint(a: str, b: str | None) -> str:
    """Return a string lexicographically between *a* and *b*.

    If *b* is None, return a string after *a*.
    Both *a* and *b* must use characters from ``_DIGITS`` and *a* < *b*.
    """
    if b is not None and a >= b:
        msg = f"a ({a!r}) must be less than b ({b!r})"
        raise ValueError(msg)

    if b is None:
        # Append a middle character
        return a + _DIGITS[_BASE // 2]

    # Find the first index where a and b differ
    n = max(len(a), len(b))
    a_padded = a.ljust(n, _DIGITS[0])
    b_padded = b.ljust(n, _DIGITS[0])

    common_prefix = []
    for i in range(n):
        if a_padded[i] == b_padded[i]:
            common_prefix.append(a_padded[i])
        else:
            break

    prefix = "".join(common_prefix)
    idx = len(prefix)
    a_digit = _DIGITS.index(a_padded[idx]) if idx < len(a_padded) else 0
    b_digit = _DIGITS.index(b_padded[idx]) if idx < len(b_padded) else _BASE

    if b_digit - a_digit > 1:
        mid = (a_digit + b_digit) // 2
        return prefix + _DIGITS[mid]

    # Digits are adjacent — need to go deeper
    result = prefix + _DIGITS[a_digit]
    # Now find midpoint between remaining suffix of a and the ceiling
    rest_a = a_padded[idx + 1 :] if idx + 1 < len(a_padded) else ""
    return result + _midpoint_after(rest_a)


def _midpoint_after(s: str) -> str:
    """Return a suffix that sorts after *s*."""
    if not s:
        return _DIGITS[_BASE // 2]

    last_idx = _DIGITS.index(s[-1])
    if last_idx < _BASE - 1:
        return s[:-1] + _DIGITS[(last_idx + _BASE) // 2]

    # Last char is max — recurse on prefix
    return s + _DIGITS[_BASE // 2]


def generate_position_between(before: str | None, after: str | None) -> str:
    """Generate a fractional index key between two existing keys."""
    if before is None and after is None:
        return "a" + _DIGITS[_BASE // 2]

    if before is None:
        assert after is not None
        first = _DIGITS.index(after[0]) if after else _BASE // 2
        if first > 0:
            return _DIGITS[first // 2] + _DIGITS[_BASE // 2]
        return _midpoint("", after)

    if after is None:
        return _midpoint(before, None)

    return _midpoint(before, after)


def generate_position_after(last: str | None) -> str:
    """Generate a position key that sorts after *last* (or a first key if None)."""
    return generate_position_between(last, None)


__all__ = [
    "generate_position_after",
    "generate_position_between",
]
