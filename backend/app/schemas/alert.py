"""Pydantic schemas for Alert creation, resolution, and API responses."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

SeverityLiteral = Literal["info", "warning", "critical"]


class AlertCreate(BaseModel):
    """Payload to manually create an alert (e.g. from dashboard)."""
    device_uuid: str
    severity: SeverityLiteral = "warning"
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    metric_id: Optional[int] = None


class AlertResolve(BaseModel):
    """Payload to resolve an alert."""
    alert_id: int


class AlertOut(BaseModel):
    """Alert representation returned by the API."""
    id: int
    device_id: int
    metric_id: Optional[int]
    severity: str
    title: str
    message: str
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Paginated alert list for a device."""
    device_id: int
    total: int
    alerts: list[AlertOut]
