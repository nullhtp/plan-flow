"""Artifact service: business logic for task artifact CRUD."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.boards.artifact_repository import ArtifactRepository
from app.domains.boards.models import Artifact
from app.domains.boards.ownership import ArtifactNotFoundError


async def create_artifact(
    session: AsyncSession,
    *,
    task_id: str,
    title: str,
    content: str,
    content_type: str = "text/markdown",
    created_by: str = "ai",
) -> Artifact:
    """Create a new artifact on a task."""
    repo = ArtifactRepository(session)
    artifact = await repo.create(
        task_id=task_id,
        title=title,
        content=content,
        content_type=content_type,
        created_by=created_by,
    )
    await session.commit()
    return artifact


async def list_artifacts(
    session: AsyncSession,
    task_id: str,
) -> list[Artifact]:
    """List all artifacts for a task."""
    repo = ArtifactRepository(session)
    return await repo.list_by_task(task_id)


async def get_artifact(
    session: AsyncSession,
    artifact_id: str,
) -> Artifact:
    """Get a single artifact by ID. Raises ArtifactNotFoundError if not found."""
    repo = ArtifactRepository(session)
    artifact = await repo.get_by_id(artifact_id)
    if artifact is None:
        raise ArtifactNotFoundError
    return artifact


async def delete_artifact(
    session: AsyncSession,
    artifact_id: str,
) -> None:
    """Delete an artifact. Raises ArtifactNotFoundError if not found."""
    repo = ArtifactRepository(session)
    artifact = await repo.get_by_id(artifact_id)
    if artifact is None:
        raise ArtifactNotFoundError
    await repo.delete(artifact_id)
    await session.commit()


async def count_artifacts(
    session: AsyncSession,
    task_id: str,
) -> int:
    """Count artifacts for a task."""
    repo = ArtifactRepository(session)
    return await repo.count_by_task(task_id)
