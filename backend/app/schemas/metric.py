"""Pydantic schemas for Metric ingestion and API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class MetricIngest(BaseModel):
    """
    Payload the agent POSTs every 5 seconds.
    Mirrors the AgentPayload structure from agent/models/metrics.py.
    Only the fields we need to index are typed; the rest lands in raw_payload.
    """
    device_uuid: str
    timestamp_utc: str
    # Top-level quick-access fields (extracted for fast queries)
    cpu_usage_percent: Optional[float] = None
    ram_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_recv: Optional[int] = None
    upload_speed_bps: Optional[float] = None
    download_speed_bps: Optional[float] = None
    battery_percent: Optional[float] = None
    uptime_seconds: Optional[float] = None
    total_processes: Optional[int] = None
    suspicious_process_count: Optional[int] = None
    # Full payload stored verbatim as JSON text
    raw_payload: Optional[Dict[str, Any]] = None


class MetricOut(BaseModel):
    """Metric snapshot returned by the API."""
    id: int
    device_id: int
    collected_at: Optional[datetime]
    created_at: datetime
    cpu_usage_percent: Optional[float]
    ram_usage_percent: Optional[float]
    disk_usage_percent: Optional[float]
    network_bytes_sent: Optional[int]
    network_bytes_recv: Optional[int]
    upload_speed_bps: Optional[float]
    download_speed_bps: Optional[float]
    battery_percent: Optional[float]
    uptime_seconds: Optional[float]
    total_processes: Optional[int]
    suspicious_process_count: Optional[int]

    model_config = {"from_attributes": True}


class MetricHistoryResponse(BaseModel):
    """Paginated history response for a device."""
    device_id: int
    total_stored: int
    metrics: List[MetricOut]
