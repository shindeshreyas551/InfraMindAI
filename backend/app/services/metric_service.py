"""
Metric Service — ingest telemetry from agents and serve historical/latest data.

Design decisions:
  - `ingest_metric` resolves device_uuid → DB device_id before storing.
    If the device is not registered yet it returns 404 (agents must register first).
  - Hot numeric columns are extracted from the payload on ingest so the
    dashboard can query them with plain SQL; the full JSON is preserved in
    `raw_payload` for forensic replay and future schema evolution.
  - `disk_usage_percent` is averaged across all partitions in the payload.
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.metric import Metric
from app.repositories.device_repository import device_repository
from app.repositories.metric_repository import metric_repository
from app.schemas.metric import MetricIngest, MetricHistoryResponse
from app.services import alert_service


def ingest_metric(db: Session, payload: MetricIngest) -> Metric:
    """
    Validate, resolve device, extract key indicators, persist, and return the Metric row.
    """
    # Resolve device UUID → DB device
    device = device_repository.get_by_uuid(db, payload.device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Device '{payload.device_uuid}' is not registered. "
                "The agent must call POST /devices/register first."
            ),
        )

    # Update device heartbeat on every telemetry push
    device_repository.update_heartbeat(db, device, is_online=True)

    # Parse collected_at timestamp
    collected_at: Optional[datetime] = None
    try:
        collected_at = datetime.fromisoformat(payload.timestamp_utc)
    except (ValueError, TypeError):
        collected_at = datetime.now(timezone.utc)

    # Compute average disk usage from raw payload partitions (if available)
    disk_pct: Optional[float] = payload.disk_usage_percent
    if disk_pct is None and payload.raw_payload:
        try:
            partitions = payload.raw_payload.get("disk", {}).get("partitions", [])
            if partitions:
                disk_pct = round(
                    sum(p.get("usage_percent", 0) for p in partitions) / len(partitions), 2
                )
        except Exception:
            pass

    # Serialize raw_payload dict → JSON text
    raw_text: Optional[str] = None
    if payload.raw_payload:
        try:
            raw_text = json.dumps(payload.raw_payload, default=str)
        except Exception:
            raw_text = str(payload.raw_payload)

    metric = Metric(
        device_id=device.id,
        collected_at=collected_at,
        cpu_usage_percent=payload.cpu_usage_percent,
        ram_usage_percent=payload.ram_usage_percent,
        disk_usage_percent=disk_pct,
        network_bytes_sent=payload.network_bytes_sent,
        network_bytes_recv=payload.network_bytes_recv,
        upload_speed_bps=payload.upload_speed_bps,
        download_speed_bps=payload.download_speed_bps,
        battery_percent=payload.battery_percent,
        uptime_seconds=payload.uptime_seconds,
        total_processes=payload.total_processes,
        suspicious_process_count=payload.suspicious_process_count,
        raw_payload=raw_text,
    )
    saved_metric = metric_repository.create(db, obj=metric)

    # Evaluate thresholds and auto-generate alerts (non-blocking)
    try:
        alert_service.evaluate_thresholds(db, device.id, saved_metric)
    except Exception:
        pass

    # Broadcast to WebSocket subscribers
    # Python 3.10+: asyncio.get_event_loop() raises RuntimeError from a ThreadPoolExecutor
    # thread. We use a pre-captured loop reference stored during app startup instead.
    try:
        from app.api.v1.endpoints.ws import ws_manager
        if ws_manager.subscriber_count(payload.device_uuid) > 0:
            metric_dict = {
                "type": "metric",
                "device_uuid": payload.device_uuid,
                "id": saved_metric.id,
                "collected_at": saved_metric.collected_at.isoformat() if saved_metric.collected_at else None,
                "cpu_usage_percent": saved_metric.cpu_usage_percent,
                "ram_usage_percent": saved_metric.ram_usage_percent,
                "disk_usage_percent": saved_metric.disk_usage_percent,
                "network_bytes_sent": saved_metric.network_bytes_sent,
                "network_bytes_recv": saved_metric.network_bytes_recv,
                "upload_speed_bps": saved_metric.upload_speed_bps,
                "download_speed_bps": saved_metric.download_speed_bps,
                "battery_percent": saved_metric.battery_percent,
                "total_processes": saved_metric.total_processes,
                "suspicious_process_count": saved_metric.suspicious_process_count,
                "uptime_seconds": saved_metric.uptime_seconds,
            }
            from app.core.event_loop import get_main_loop
            loop = get_main_loop()
            if loop and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast(payload.device_uuid, metric_dict),
                    loop,
                )
    except Exception:
        pass

    return saved_metric


def get_latest_metric(db: Session, device_uuid: str) -> Metric:
    """Return the most recent metric for a device or raise 404."""
    device = device_repository.get_by_uuid(db, device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_uuid}' not found.")
    metric = metric_repository.get_latest_for_device(db, device.id)
    if not metric:
        raise HTTPException(status_code=404, detail="No metrics found for this device yet.")
    return metric


def get_metric_history(
    db: Session, device_uuid: str, limit: int = 100
) -> MetricHistoryResponse:
    """Return the last N metric snapshots for a device."""
    device = device_repository.get_by_uuid(db, device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_uuid}' not found.")
    metrics = metric_repository.get_history_for_device(db, device.id, limit=limit)
    total = metric_repository.get_by_device_count(db, device.id)
    return MetricHistoryResponse(device_id=device.id, total_stored=total, metrics=metrics)
