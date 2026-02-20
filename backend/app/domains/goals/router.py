from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.domains.auth.deps import CurrentUser
from app.domains.goals.schemas import (
    AnswerResponse,
    AnswerSubmission,
    GoalCreate,
    GoalQuestionsResponse,
    GoalRejectionResponse,
    GoalResponse,
    QuestionSchema,
    ReadinessSchema,
)
from app.domains.goals.service import (
    GoalNotFoundError,
    GoalStatusError,
    create_goal,
    get_goal,
    submit_answers,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GoalQuestionsResponse},
        422: {"model": GoalRejectionResponse},
    },
)
async def create_goal_endpoint(
    body: GoalCreate,
    request: Request,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GoalQuestionsResponse | GoalRejectionResponse:
    """Create a new goal from raw text. Runs AI classification + question generation."""
    from app.domains.ai.service import AIOutputError

    # Extract client IP for geolocation fallback
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host

    try:
        goal, result = await create_goal(
            session,
            current_user.id,
            body.original_input,
            user_meta=body.user_meta,
            client_ip=client_ip,
        )
    except AIOutputError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI processing failed. Please try again.",
        ) from None

    if result.is_rejected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=GoalRejectionResponse(
                rejection_reason=result.rejection_reason
                or "This goal is too vague to create a plan.",
                refinement_suggestions=result.refinement_suggestions or [],
            ).model_dump(),
        )

    questions = [
        QuestionSchema.model_validate(q.model_dump()) for q in result.questions
    ]

    readiness = None
    if result.readiness:
        readiness = ReadinessSchema.model_validate(result.readiness.model_dump())

    return GoalQuestionsResponse(
        goal_id=goal.id,
        title=goal.title,
        status=goal.status,
        questions=questions,
        readiness=readiness,
    )


@router.post("/{goal_id}/answers", response_model=AnswerResponse)
async def submit_answers_endpoint(
    goal_id: str,
    body: AnswerSubmission,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnswerResponse:
    """Submit answers to a goal's questions.

    Returns next follow-up questions and readiness assessment.
    The goal stays in 'questioning' status until the user triggers board generation.
    """
    try:
        goal, next_questions, follow_up_output = await submit_answers(
            session,
            goal_id,
            current_user.id,
            body.answers,
            body.round,
        )
    except GoalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        ) from None
    except GoalStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None

    next_question_schemas = [
        QuestionSchema.model_validate(q.model_dump()) for q in next_questions
    ]

    readiness = None
    if follow_up_output and follow_up_output.readiness:
        readiness = ReadinessSchema.model_validate(
            follow_up_output.readiness.model_dump()
        )

    return AnswerResponse(
        next_questions=next_question_schemas,
        readiness=readiness,
        next_round=body.round + 1,
        status=goal.status,
    )


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal_endpoint(
    goal_id: str,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GoalResponse:
    """Get a goal by ID."""
    try:
        goal = await get_goal(session, goal_id, current_user.id)
    except GoalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found",
        ) from None

    return GoalResponse.model_validate(goal)
