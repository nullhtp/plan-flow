"""Data-access layer for board share links."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import BoardShare


class ShareRepository:
    """Encapsulates all database queries for :class:`BoardShare`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_board_id(self, board_id: str) -> BoardShare | None:
        stmt = select(BoardShare).where(BoardShare.board_id == board_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> BoardShare | None:
        stmt = select(BoardShare).where(BoardShare.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, board_id: str, created_by: str) -> BoardShare:
        """Create or regenerate a share link for a board."""
        existing = await self.get_by_board_id(board_id)
        if existing is not None:
            existing.token = secrets.token_urlsafe(32)
            self.session.add(existing)
            await self.session.flush()
            return existing

        share = BoardShare(
            board_id=board_id,
            token=secrets.token_urlsafe(32),
            created_by=created_by,
        )
        self.session.add(share)
        await self.session.flush()
        return share

    async def delete(self, board_id: str) -> bool:
        share = await self.get_by_board_id(board_id)
        if share is None:
            return False
        await self.session.delete(share)
        await self.session.flush()
        return True
