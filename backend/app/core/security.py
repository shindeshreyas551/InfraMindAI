"""
Security utilities: password hashing and JWT token management.

Design decisions:
- passlib[bcrypt] handles password hashing — bcrypt is the industry standard.
- python-jose handles JWT encoding/decoding.
- Access tokens are short-lived (configurable, default 24 h).
- Refresh tokens are long-lived (configurable, default 7 days).
- Token payload carries `sub` (user ID as string) and `type` field so
  the backend can distinguish access vs refresh tokens on validation.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Returns bcrypt-hashed version of the given plain password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Returns True if plain_password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────────────
TokenType = Literal["access", "refresh"]


def create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Creates a signed JWT.

    Args:
        subject:      The user's ID (stored as the `sub` claim).
        token_type:   "access" or "refresh" — stored in the `type` claim.
        expires_delta: Custom TTL; defaults to settings value if None.

    Returns:
        A signed JWT string.
    """
    if expires_delta is None:
        minutes = (
            settings.ACCESS_TOKEN_EXPIRE_MINUTES
            if token_type == "access"
            else settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
        expires_delta = timedelta(minutes=minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT.

    Returns:
        The decoded payload dictionary.

    Raises:
        JWTError: if the token is expired, tampered, or malformed.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def create_access_token(user_id: int) -> str:
    """Convenience wrapper — creates a short-lived access token."""
    return create_token(subject=str(user_id), token_type="access")


def create_refresh_token(user_id: int) -> str:
    """Convenience wrapper — creates a long-lived refresh token."""
    return create_token(subject=str(user_id), token_type="refresh")
