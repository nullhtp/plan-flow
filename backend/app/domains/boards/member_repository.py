"""Data-access layer for board members."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import BoardMember


class MemberRepository:
    """Encapsulates all database queries for :class:`BoardMember`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_board_and_user(
        self, board_id: str, user_id: str
    ) -> BoardMember | None:
        stmt = select(BoardMember).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_member(self, board_id: str, user_id: str) -> bool:
        return await self.get_by_board_and_user(board_id, user_id) is not None

    async def list_by_board(self, board_id: str) -> list[BoardMember]:
        stmt = (
            select(BoardMember)
            .where(BoardMember.board_id == board_id)
            .order_by(BoardMember.joined_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, board_id: str, user_id: str) -> BoardMember:
        member = BoardMember(board_id=board_id, user_id=user_id)
        self.session.add(member)
        await self.session.flush()
        return member

    async def delete(self, board_id: str, user_id: str) -> bool:
        member = await self.get_by_board_and_user(board_id, user_id)
        if member is None:
            return False
        await self.session.delete(member)
        await self.session.flush()
        return True

    async def list_boards_for_user(self, user_id: str) -> list[str]:
        """Return board IDs where user is a collaborator."""
        stmt = (
            select(BoardMember.board_id)
            .where(BoardMember.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
