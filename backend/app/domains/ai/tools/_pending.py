"""Shared helper for creating PendingAction records from tools."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import PendingAction


async def create_pending_action(
    *,
    db: AsyncSession,
    user_id: str,
    thread_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    description: str,
) -> PendingAction:
    """Create a PendingAction and expire any existing one."""
    # Expire existing pending actions on this thread
    stmt = (
        update(PendingAction)
        .where(
            PendingAction.thread_id == thread_id,  # pyright: ignore[reportArgumentType]
            PendingAction.status == "pending",  # pyright: ignore[reportArgumentType]
        )
        .values(status="expired")
    )
    await db.execute(stmt)

    now = datetime.now(UTC)
    action = PendingAction(
        user_id=user_id,
        thread_id=thread_id,
        tool_name=tool_name,
        tool_args=tool_args,
        description=description,
        status="pending",
        created_at=now,
        expires_at=now + timedelta(minutes=10),
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action
