"""
Authentication Service — register, login, refresh, and current-user logic.

Design decisions:
  - All DB mutation goes through the repository layer, never raw SQL.
  - `get_current_user` is a FastAPI dependency injected into protected routes.
  - Token type claim ("access" vs "refresh") is validated explicitly so a
    refresh token cannot be used as an access token and vice versa.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate, Token

# FastAPI OAuth2 scheme — points to the login endpoint for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Register ──────────────────────────────────────────────────────────────────
def register_user(db: Session, payload: UserCreate) -> User:
    """Create a new user. Raises 400 if the email is already taken."""
    if user_repository.email_exists(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    return user_repository.create(db, obj=new_user)


# ── Login ─────────────────────────────────────────────────────────────────────
def login_user(db: Session, email: str, password: str) -> Token:
    """Validate credentials and return access + refresh token pair."""
    user = user_repository.get_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled.",
        )
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ── Refresh token ─────────────────────────────────────────────────────────────
def refresh_access_token(db: Session, refresh_token: str) -> Token:
    """Exchange a valid refresh token for a new access token pair."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_error
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_error

    user = user_repository.get(db, user_id)
    if not user or not user.is_active:
        raise credentials_error

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ── Current user dependency ───────────────────────────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: decodes the access token and returns the User object."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_error
        user_id: Optional[int] = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_error

    user = user_repository.get(db, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user
