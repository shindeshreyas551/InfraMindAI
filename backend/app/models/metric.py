"""
Metric ORM Model.

Stores one telemetry snapshot per agent collection pass (every 5 seconds).

Design decisions:
  - Key numeric indicators (CPU, RAM, disk %) are stored as dedicated
    float columns so the dashboard can run fast aggregate SQL queries
    (e.g. AVG cpu_usage_percent over last 5 minutes) without JSON parsing.
  - The complete raw JSON payload from the agent is stored in `raw_payload`
    (TEXT) so no data is ever discarded — future columns can be added via
    Alembic migration without losing historical detail.
  - `collected_at` is the agent-side UTC timestamp from the payload.
  - `created_at` is the server-side insert time (for ordering/deduplication).

Relationships:
  - Belongs to one Device (many-to-one).
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.device import Device


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # FK to the device that sent this metric snapshot
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Agent-reported collection timestamp (UTC ISO 8601)
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Server insert timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # ── Key indicators (hot columns for dashboard queries) ────────────────────
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # average across partitions
    network_bytes_sent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    network_bytes_recv: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    upload_speed_bps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    download_speed_bps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    uptime_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_processes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    suspicious_process_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Full raw payload (JSON text) ──────────────────────────────────────────
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="metrics")

    def __repr__(self) -> str:
        return (
            f"<Metric id={self.id} device_id={self.device_id} "
            f"cpu={self.cpu_usage_percent}% ram={self.ram_usage_percent}%>"
        )
