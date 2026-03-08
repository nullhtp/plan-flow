"""HTTP endpoints for the templates domain."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
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
    TemplateAnswerResponse,
    TemplateAnswerSubmission,
    TemplateCategoryBrief,
    TemplateCategoryResponse,
    TemplateClassificationData,
    TemplateClassifyRequest,
    TemplateClassifyResponse,
    TemplateCreateRequest,
    TemplateCreatorResponse,
    TemplateDetailResponse,
    TemplateEdgeResponse,
    TemplateGenerateStreamRequest,
    TemplateListItemResponse,
    TemplateListResponse,
    TemplateQuestionSchema,
    TemplateReadinessSchema,
    TemplateSubtaskResponse,
    TemplateTaskResponse,
    TemplateUpdateRequest,
    UpdateTemplateStructureRequest,
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
    update_template_structure,
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
        ) from None
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
        ) from None
    return ContentExtractionResponse(
        content=result.content,
        source_type=result.source_type,
        source_name=result.source_name,
        char_count=result.char_count,
        truncated=result.truncated,
    )


@router.post("/classify", response_model=TemplateClassifyResponse)
async def classify_template_endpoint(
    body: TemplateClassifyRequest,
    current_user: CurrentUser,
) -> TemplateClassifyResponse:
    """Classify template input and generate initial questions.

    Accepts description-based or content-based inputs. Returns classification
    data, initial questions, and readiness assessment. Session state is
    returned to the client for subsequent requests (no server-side session).
    """
    from app.domains.ai.schemas import ClassificationOutput
    from app.domains.ai.service import (
        AIOutputError,
        classify_template_content,
        generate_template_questions,
    )

    # Step 1: Classify the input
    raw_input = body.content
    try:
        classification: ClassificationOutput = await classify_template_content(
            raw_input=raw_input,
            input_type=body.input_type,
            content=body.content if body.input_type != "describe" else None,
            title_hint=body.title,
        )
    except AIOutputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Classification failed: {e}",
        ) from None

    # Check for rejection (too vague)
    if classification.confidence < 0.3:
        return TemplateClassifyResponse(
            classification=TemplateClassificationData(
                domain=classification.domain,
                complexity=classification.complexity,
                confidence=classification.confidence,
                dimensions=classification.dimensions,
                suggested_title=classification.suggested_title,
                language=classification.language,
            ),
            questions=[],
            is_rejected=True,
            rejection_reason=classification.rejection_reason
            or "This input is too vague to create a useful template.",
            refinement_suggestions=classification.refinement_suggestions,
        )

    # Step 2: Generate initial questions
    content_for_questions = body.content if body.input_type != "describe" else None
    try:
        questions_output = await generate_template_questions(
            raw_input=raw_input,
            classification=classification,
            content=content_for_questions,
        )
    except AIOutputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Question generation failed: {e}",
        ) from None

    questions = [
        TemplateQuestionSchema.model_validate(q.model_dump())
        for q in questions_output.questions
    ]

    readiness = None
    if questions_output.readiness:
        readiness = TemplateReadinessSchema.model_validate(
            questions_output.readiness.model_dump()
        )

    return TemplateClassifyResponse(
        classification=TemplateClassificationData(
            domain=classification.domain,
            complexity=classification.complexity,
            confidence=classification.confidence,
            dimensions=classification.dimensions,
            suggested_title=classification.suggested_title,
            language=classification.language,
        ),
        questions=questions,
        readiness=readiness,
    )


@router.post("/answers", response_model=TemplateAnswerResponse)
async def submit_template_answers_endpoint(
    body: TemplateAnswerSubmission,
    current_user: CurrentUser,
) -> TemplateAnswerResponse:
    """Submit answers to template questions and get follow-up questions.

    Session state (classification, previous rounds, content) is passed in
    the request body. Max 1 follow-up round (round 2) is supported.
    """
    from app.domains.ai.schemas import ClassificationOutput
    from app.domains.ai.service import generate_template_follow_up_questions

    # Reconstruct ClassificationOutput from the request data
    classification = ClassificationOutput(
        reasoning="",
        domain=body.classification.domain,
        complexity=body.classification.complexity,
        confidence=body.classification.confidence,
        dimensions=body.classification.dimensions,
        suggested_title=body.classification.suggested_title,
        language=body.classification.language,
    )

    # Build rounds data for the follow-up generator
    # Current round answers are added to the rounds list
    current_round = {
        "round": body.round,
        "questions": [
            r.model_dump() if hasattr(r, "model_dump") else r
            for r in body.previous_rounds[-1].get("questions", [])
        ]
        if body.previous_rounds
        else [],
        "answers": body.answers,
    }

    # Build the full rounds list with answers merged in
    all_rounds: list[dict[str, Any]] = []
    if body.previous_rounds:
        for r in body.previous_rounds:
            round_data = dict(r)
            if r.get("round") == body.round:
                round_data["answers"] = body.answers
            all_rounds.append(round_data)
    else:
        all_rounds.append(current_round)

    # Max 1 follow-up round — if this is round 2 or later, no more questions
    if body.round >= 2:
        return TemplateAnswerResponse(
            next_questions=[],
            readiness=None,
            next_round=body.round + 1,
            is_ready=True,
        )

    # Generate follow-up questions (round 2)
    follow_up = await generate_template_follow_up_questions(
        raw_input=body.raw_input,
        classification=classification,
        rounds=all_rounds,
        content=body.content,
    )

    if follow_up is None or not follow_up.questions:
        return TemplateAnswerResponse(
            next_questions=[],
            readiness=None,
            next_round=body.round + 1,
            is_ready=True,
        )

    next_questions = [
        TemplateQuestionSchema.model_validate(q.model_dump())
        for q in follow_up.questions
    ]

    readiness = None
    if follow_up.readiness:
        readiness = TemplateReadinessSchema.model_validate(
            follow_up.readiness.model_dump()
        )

    return TemplateAnswerResponse(
        next_questions=next_questions,
        readiness=readiness,
        next_round=body.round + 1,
        is_ready=False,
    )


@router.post("/generate/stream")
async def generate_template_stream_endpoint(
    body: TemplateGenerateStreamRequest,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Generate a template using AI, streaming progress via SSE.

    Returns a text/event-stream response with events:
    - research_started, research_progress, research_complete
    - skeleton_ready: template title, tasks (id, title, depends_on, is_goal_node)
    - task_enriched: task_id, description, priority, estimated_minutes, subtasks
    - generation_complete: template title, failed_tasks
    - generation_error: error message
    """
    from app.domains.ai.service import generate_template_stream

    # Format Q&A pairs from the rounds data
    qa_lines: list[str] = []
    for r in body.qa_rounds:
        questions = r.get("questions", [])
        answers = r.get("answers", {})
        for q in questions:
            qid = q.get("id", "")
            text = q.get("text", "")
            answer = answers.get(qid, "(not answered)")
            qa_lines.append(f"Q: {text}\nA: {answer}")
    qa_pairs = "\n".join(qa_lines) if qa_lines else "(no questions answered)"

    return StreamingResponse(
        generate_template_stream(
            raw_input=body.raw_input,
            domain=body.classification.domain,
            complexity=body.classification.complexity,
            dimensions=body.classification.dimensions,
            qa_pairs=qa_pairs,
            language=body.classification.language,
            content=body.content,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate", response_model=GenerateTemplateResponse)
async def generate_template_endpoint(
    body: GenerateTemplateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GenerateTemplateResponse:
    """Generate a template DAG from text content using AI (legacy)."""
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
        ) from None

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
                    GenerateTemplateSubtaskResponse(title=s.title) for s in t.subtasks
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
    """Save a generated (and optionally edited) template.

    Accepts the full edited template structure including tasks with
    priority, estimated_minutes, and modified dependencies from the
    DAG editor. Optionally creates a board from the saved template.
    """
    tasks_dicts = [
        {
            "id": t.id or f"t{i}",
            "title": t.title,
            "description": t.description,
            "is_goal_node": t.is_goal_node,
            "depends_on": t.depends_on,
            "subtasks": [{"title": s.title} for s in t.subtasks],
            "priority": t.priority,
            "estimated_minutes": t.estimated_minutes,
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

    # Optionally create a board from the saved template
    if body.create_board:
        await create_board_from_template(
            session,
            template_id=template.id,
            user_id=current_user.id,
            title=body.title,
        )

    full = await get_template(session, template.id, current_user.id)
    return _build_detail_response(full, current_user)


# ── Template CRUD Endpoints ─────────────────────────────


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateDetailResponse,
)
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
                )
                if t.category
                else None,
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


@router.put("/{template_id}/structure", response_model=TemplateDetailResponse)
async def update_template_structure_endpoint(
    template_id: str,
    body: UpdateTemplateStructureRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateDetailResponse:
    """Replace the entire task structure of a template.

    Validates ownership and DAG structure, then deletes all existing
    tasks/deps/subtasks and inserts the new structure in a single transaction.
    """
    tasks_dicts = [
        {
            "id": t.id or f"t{i}",
            "title": t.title,
            "description": t.description,
            "is_goal_node": t.is_goal_node,
            "depends_on": t.depends_on,
            "subtasks": [{"title": s.title} for s in t.subtasks],
            "priority": t.priority,
            "estimated_minutes": t.estimated_minutes,
        }
        for i, t in enumerate(body.tasks)
    ]

    await update_template_structure(
        session,
        template_id=template_id,
        user_id=current_user.id,
        tasks_input=tasks_dicts,
    )

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
        )
        if t.category
        else None,
        task_count=t.task_count,
        creator=TemplateCreatorResponse(
            id=t.user_id,
            email=creator_email,
        ),
        tasks=tasks,
        edges=edges,
        created_at=t.created_at,
    )
