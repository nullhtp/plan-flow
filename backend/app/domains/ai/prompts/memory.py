from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.ai.models import Memory


def format_memory_block(memories: list[Memory]) -> str:
    """Format retrieved memories into a text block for AI prompt injection.

    Returns a formatted "Relevant user memories:" block with each memory
    as a bullet point, or an empty string if the memories list is empty.
    """
    if not memories:
        return ""

    lines = [f"- {m.content}" for m in memories]
    return "\nRelevant user memories:\n" + "\n".join(lines)
