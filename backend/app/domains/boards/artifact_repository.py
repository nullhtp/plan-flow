"""Repository for artifact data access."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.models import Artifact


class ArtifactRepository:
    """Data access layer for artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        task_id: str,
        title: str,
        content: str,
        content_type: str = "text/markdown",
        created_by: str = "ai",
    ) -> Artifact:
        """Create a new artifact."""
        artifact = Artifact(
            task_id=task_id,
            title=title,
            content=content,
            content_type=content_type,
            created_by=created_by,
        )
        self._session.add(artifact)
        await self._session.flush()
        return artifact

    async def list_by_task(self, task_id: str) -> list[Artifact]:
        """List all artifacts for a task, ordered by created_at desc."""
        stmt = (
            select(Artifact)
            .where(Artifact.task_id == task_id)  # pyright: ignore[reportArgumentType]
            .order_by(Artifact.created_at.desc())  # pyright: ignore[reportAttributeAccessIssue]
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, artifact_id: str) -> Artifact | None:
        """Get a single artifact by ID."""
        return await self._session.get(Artifact, artifact_id)

    async def delete(self, artifact_id: str) -> None:
        """Delete an artifact by ID."""
        artifact = await self._session.get(Artifact, artifact_id)
        if artifact is not None:
            await self._session.delete(artifact)
            await self._session.flush()

    async def count_by_task(self, task_id: str) -> int:
        """Count artifacts for a task."""
        stmt = (
            select(func.count())
            .select_from(Artifact)
            .where(Artifact.task_id == task_id)  # pyright: ignore[reportArgumentType]
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
