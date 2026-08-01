"""
AIAnalysis ORM Model.

Stores AI-generated incident analysis and recommendations for a device.

Design decisions:
  - `provider` field records which AI backend produced the analysis
    (gemini / openai / claude / ollama) — supports the pluggable AI layer
    planned for a future phase without schema changes.
  - `metric_id` is nullable — analysis can be triggered on aggregate data,
    not just a single metric snapshot.
  - `analysis_text` stores the free-form AI output.
  - `recommendation` stores the actionable suggestion extracted from the AI.
  - `confidence_score` is optional — some providers return a confidence level.

This model is a placeholder that is fully wired up for the AI phase.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.device import Device


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("metrics.id", ondelete="SET NULL"), nullable=True
    )

    # AI provider: "gemini" | "openai" | "claude" | "ollama"
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")

    analysis_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="ai_analyses")

    def __repr__(self) -> str:
        return f"<AIAnalysis id={self.id} provider={self.provider!r} device_id={self.device_id}>"
