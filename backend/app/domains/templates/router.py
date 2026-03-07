"""HTTP endpoints for the templates domain."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domains.auth.deps import CurrentUser
from app.domains.auth.models import User
from app.domains.templates.schemas import (
    ContentExtractionResponse,
    CreateBoardFromTemplateRequest,
    CreateBoardFromTemplateResponse,
    ExtractUrlRequest,
    GenerateTemplateRequest,
    GenerateTemplateResponse,
    GenerateTemplateSubtaskResponse,
    GenerateTemplateTaskResponse,
    SaveGeneratedTemplateRequest,
    TemplateCategoryBrief,
    TemplateCategoryResponse,
    TemplateCreateRequest,
    TemplateCreatorResponse,
    TemplateDetailResponse,
    TemplateEdgeResponse,
    TemplateListItemResponse,
    TemplateListResponse,
    TemplateSubtaskResponse,
    TemplateTaskResponse,
    TemplateUpdateRequest,
)
from app.domains.templates.service import (
    create_board_from_template,
    create_template_from_board,
    delete_template,
    get_template,
    list_categories,
    list_templates,
    save_generated_template,
    update_template,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


# ── Category Endpoints ──────────────────────────────────


@router.get("/categories", response_model=list[TemplateCategoryResponse])
async def list_categories_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[TemplateCategoryResponse]:
    """List all template categories with public template counts."""
    categories = await list_categories(session)
    return [TemplateCategoryResponse(**c) for c in categories]


# ── Template Generation Endpoints ──────────────────────


@router.post(
    "/extract-content/file",
    response_model=ContentExtractionResponse,
)
async def extract_file_endpoint(
    file: UploadFile,
    current_user: CurrentUser,
) -> ContentExtractionResponse:
    """Extract text content from an uploaded file (PDF, DOCX, TXT, MD)."""
    from app.domains.ai.content_extraction import (
        ExtractionError,
        extract_from_file,
    )

    data = await file.read()
    try:
        result = extract_from_file(data, file.filename or "unknown")
    except ExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    return ContentExtractionResponse(
        content=result.content,
        source_type=result.source_type,
        source_name=result.source_name,
        char_count=result.char_count,
        truncated=result.truncated,
    )


@router.post(
    "/extract-content/url",
    response_model=ContentExtractionResponse,
)
async def extract_url_endpoint(
    body: ExtractUrlRequest,
    current_user: CurrentUser,
) -> ContentExtractionResponse:
    """Extract text content from a URL."""
    from app.domains.ai.content_extraction import (
        ExtractionError,
        extract_from_url,
    )

    try:
        result = await extract_from_url(body.url)
    except ExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    return ContentExtractionResponse(
        content=result.content,
        source_type=result.source_type,
        source_name=result.source_name,
        char_count=result.char_count,
        truncated=result.truncated,
    )


@router.post("/generate", response_model=GenerateTemplateResponse)
async def generate_template_endpoint(
    body: GenerateTemplateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GenerateTemplateResponse:
    """Generate a template DAG from text content using AI."""
    from app.domains.ai.service import AIOutputError, generate_template_from_content

    # Get category slugs for the prompt
    categories = await list_categories(session)
    category_slugs = [c["slug"] for c in categories]

    try:
        output = await generate_template_from_content(
            content=body.content,
            category_slugs=category_slugs,
            title_hint=body.title or "",
        )
    except AIOutputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Template generation failed: {e}",
        )

    return GenerateTemplateResponse(
        suggested_title=output.suggested_title,
        suggested_description=output.suggested_description,
        suggested_category_slug=output.suggested_category_slug,
        tasks=[
            GenerateTemplateTaskResponse(
                id=t.id,
                title=t.title,
                description=t.description,
                is_goal_node=t.is_goal_node,
                depends_on=t.depends_on,
                subtasks=[
                    GenerateTemplateSubtaskResponse(title=s.title)
                    for s in t.subtasks
                ],
            )
            for t in output.tasks
        ],
        task_count=len(output.tasks),
    )


@router.post(
    "/save-generated",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateDetailResponse,
)
async def save_generated_template_endpoint(
    body: SaveGeneratedTemplateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateDetailResponse:
    """Save a generated (and optionally edited) template."""
    tasks_dicts = [
        {
            "id": f"t{i}",
            "title": t.title,
            "description": t.description,
            "is_goal_node": t.is_goal_node,
            "depends_on": t.depends_on,
            "subtasks": [{"title": s.title} for s in t.subtasks],
        }
        for i, t in enumerate(body.tasks)
    ]

    template = await save_generated_template(
        session,
        user_id=current_user.id,
        title=body.title,
        tasks_input=tasks_dicts,
        description=body.description,
        category_id=body.category_id,
        visibility=body.visibility,
    )

    full = await get_template(session, template.id, current_user.id)
    return _build_detail_response(full, current_user)


# ── Template CRUD Endpoints ─────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TemplateDetailResponse)
async def create_template_endpoint(
    body: TemplateCreateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateDetailResponse:
    """Create a template from an existing board."""
    template = await create_template_from_board(
        session,
        user_id=current_user.id,
        board_id=body.board_id,
        title=body.title,
        description=body.description,
        category_id=body.category_id,
        visibility=body.visibility,
    )
    # Re-fetch with relations for full response
    full = await get_template(session, template.id, current_user.id)
    return _build_detail_response(full, current_user)


@router.get("", response_model=TemplateListResponse)
async def list_templates_endpoint(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    visibility: str = Query(default="public", pattern="^(public|mine)$"),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=50),
) -> TemplateListResponse:
    """List templates with filtering, search, and pagination."""
    result = await list_templates(
        session,
        user_id=current_user.id,
        visibility=visibility,
        category_slug=category,
        search=search,
        page=page,
        per_page=per_page,
    )

    # Enrich items with creator info
    items: list[TemplateListItemResponse] = []
    for t in result["items"]:
        creator = await session.get(User, t.user_id)
        items.append(
            TemplateListItemResponse(
                id=t.id,
                title=t.title,
                description=t.description,
                visibility=t.visibility,
                category=TemplateCategoryBrief(
                    id=t.category.id,
                    name=t.category.name,
                    slug=t.category.slug,
                ) if t.category else None,
                task_count=t.task_count,
                creator=TemplateCreatorResponse(
                    id=t.user_id,
                    email=creator.email if creator else "",
                ),
                created_at=t.created_at,
            )
        )

    return TemplateListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        total_pages=result["total_pages"],
    )


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template_endpoint(
    template_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateDetailResponse:
    """Get template detail with tasks, subtasks, and edges."""
    template = await get_template(session, template_id, current_user.id)
    return _build_detail_response(template, current_user)


@router.patch("/{template_id}", response_model=TemplateDetailResponse)
async def update_template_endpoint(
    template_id: str,
    body: TemplateUpdateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateDetailResponse:
    """Update template metadata."""
    await update_template(
        session,
        template_id=template_id,
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        category_id=body.category_id,
        visibility=body.visibility,
    )
    template = await get_template(session, template_id, current_user.id)
    return _build_detail_response(template, current_user)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_endpoint(
    template_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a template."""
    await delete_template(session, template_id, current_user.id)


@router.post(
    "/{template_id}/create-board",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateBoardFromTemplateResponse,
)
async def create_board_from_template_endpoint(
    template_id: str,
    body: CreateBoardFromTemplateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreateBoardFromTemplateResponse:
    """Create a new board (and goal) from a template."""
    result = await create_board_from_template(
        session,
        template_id=template_id,
        user_id=current_user.id,
        title=body.title,
    )
    return CreateBoardFromTemplateResponse(**result)


# ── Helpers ─────────────────────────────────────────────


def _build_detail_response(
    template: object,
    current_user: object,
) -> TemplateDetailResponse:
    """Build a TemplateDetailResponse from a loaded template."""
    from app.domains.templates.models import BoardTemplate

    t: BoardTemplate = template  # type: ignore[assignment]
    user: User = current_user  # type: ignore[assignment]

    tasks: list[TemplateTaskResponse] = []
    edges: list[TemplateEdgeResponse] = []

    for task in t.tasks:
        tasks.append(
            TemplateTaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                is_goal_node=task.is_goal_node,
                priority=task.priority,
                estimated_minutes=task.estimated_minutes,
                subtasks=[
                    TemplateSubtaskResponse(
                        id=s.id,
                        title=s.title,
                        position=s.position,
                    )
                    for s in task.subtasks
                ],
            )
        )

    for dep in t.dependencies:
        edges.append(
            TemplateEdgeResponse(
                source=dep.dependency_task_id,
                target=dep.dependent_task_id,
            )
        )

    # Get creator info — for own templates use current user, otherwise fetch
    creator_email = user.email if t.user_id == user.id else ""

    return TemplateDetailResponse(
        id=t.id,
        title=t.title,
        description=t.description,
        visibility=t.visibility,
        category=TemplateCategoryBrief(
            id=t.category.id,
            name=t.category.name,
            slug=t.category.slug,
        ) if t.category else None,
        task_count=t.task_count,
        creator=TemplateCreatorResponse(
            id=t.user_id,
            email=creator_email,
        ),
        tasks=tasks,
        edges=edges,
        created_at=t.created_at,
    )
