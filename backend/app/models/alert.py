"""
Alert ORM Model.

Stores threshold-based alerts triggered against device metrics.

Design decisions:
  - Severity levels follow standard ops: "info", "warning", "critical".
  - `is_resolved` allows alerts to be closed without deletion (full audit trail).
  - `resolved_at` is nullable — only set when is_resolved flips to True.
  - `metric_id` is nullable — alerts can be system-generated without a
    specific metric snapshot (e.g. device went offline).

This model is ready for the alerting engine in a future phase.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.metric import Metric


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("metrics.id", ondelete="SET NULL"), nullable=True
    )

    # "info" | "warning" | "critical"
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert id={self.id} severity={self.severity!r} device_id={self.device_id}>"
