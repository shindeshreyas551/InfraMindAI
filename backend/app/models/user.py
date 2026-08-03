"""
User ORM Model.

Represents a human operator who logs into the InfraMind AI dashboard.

Relationships:
  - One user owns many Devices (a user registers their machines).
  - Cascade delete: removing a user removes all their devices (and their metrics).

Fields:
  id              — Auto-increment primary key.
  email           — Unique login identifier.
  hashed_password — bcrypt hash; plain password is NEVER stored.
  full_name       — Display name shown in the dashboard.
  is_active       — Soft-disable an account without deleting it.
  is_superuser    — Future admin/role capability flag.
  created_at      — UTC timestamp of account creation.
"""

from datetime import datetime, timezone
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.device import Device


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(50), default="USER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    devices: Mapped[List["Device"]] = relationship(
        "Device", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
