from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.security import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.domains.auth.deps import CurrentUser
from app.domains.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)
from app.domains.auth.service import authenticate_user, get_user_by_id, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user_id: str) -> None:
    """Set access and refresh token cookies on the response."""
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        path="/api",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/auth/refresh",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear access and refresh token cookies."""
    response.delete_cookie(
        key="access_token",
        path="/api",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth/refresh",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """Register a new user account."""
    try:
        user = await register_user(session, body.email, body.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None

    _set_auth_cookies(response, user.id)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """Authenticate with email and password."""
    user = await authenticate_user(session, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    _set_auth_cookies(response, user.id)
    return UserResponse.model_validate(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    """Log out by clearing auth cookies."""
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully")


@router.post("/refresh", response_model=UserResponse)
async def refresh(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> UserResponse:
    """Obtain new tokens using a valid refresh token."""
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        payload = decode_token(refresh_token)
    except JWTError:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from None

    if payload.get("type") != "refresh":
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    _set_auth_cookies(response, user.id)
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
