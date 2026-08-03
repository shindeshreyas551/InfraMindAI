"""Pydantic schemas for User and authentication tokens."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── User schemas ──────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    """Payload for POST /auth/register."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., min_length=1, max_length=255)


class UserOut(BaseModel):
    """Safe user representation returned by the API (no password)."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    is_disabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Payload for POST /auth/login."""
    email: EmailStr
    password: str


# ── Token schemas ─────────────────────────────────────────────────────────────
class Token(BaseModel):
    """Returned on successful login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Payload for POST /auth/refresh."""
    refresh_token: str


class TokenData(BaseModel):
    """Decoded content of a JWT access token."""
    user_id: Optional[int] = None
