from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
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
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GoalQuestionsResponse | GoalRejectionResponse:
    """Create a new goal from raw text. Runs AI classification + question generation."""
    from app.domains.ai.service import AIOutputError

    try:
        goal, result = await create_goal(session, current_user.id, body.original_input)
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

    return GoalQuestionsResponse(
        goal_id=goal.id,
        title=goal.title,
        status=goal.status,
        questions=questions,
    )


@router.post("/{goal_id}/answers", response_model=AnswerResponse)
async def submit_answers_endpoint(
    goal_id: str,
    body: AnswerSubmission,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnswerResponse:
    """Submit answers to a goal's questions."""
    try:
        goal, follow_ups, is_complete = await submit_answers(
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

    follow_up_schemas = [
        QuestionSchema.model_validate(q.model_dump()) for q in follow_ups
    ]

    return AnswerResponse(
        is_complete=is_complete,
        follow_up_questions=follow_up_schemas,
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
