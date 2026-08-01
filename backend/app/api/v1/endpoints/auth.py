"""
Auth API endpoints — register, login, refresh token, current user.

Security:
  - POST /register and POST /login are rate-limited per IP via slowapi.
  - Rate limit: RATE_LIMIT_PER_MINUTE (default 10 requests/minute).
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.user import UserCreate, UserOut, UserLogin, Token, TokenRefresh
from app.services.auth_service import (
    register_user,
    login_user,
    refresh_access_token,
    get_current_user,
)
from app.models.user import User
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

_RATE = f"{settings.RATE_LIMIT_PER_MINUTE}/minute"


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit(_RATE)
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new InfraMind AI user account.
    Rate limited to prevent automated account creation.
    """
    return register_user(db, payload)


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive JWT tokens",
)
@limiter.limit(_RATE)
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate with email + password. Returns access and refresh tokens.
    Rate limited to prevent brute-force password attacks.
    """
    return login_user(db, payload.email, payload.password)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token using a refresh token",
)
def refresh(payload: TokenRefresh, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    return refresh_access_token(db, payload.refresh_token)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current authenticated user",
)
def me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return current_user
