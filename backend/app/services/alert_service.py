"""
Alert Service — threshold evaluation engine + CRUD operations.

Threshold defaults (all configurable in config.py):
  CPU    > 85%  → warning  | > 95%  → critical
  RAM    > 80%  → warning  | > 90%  → critical
  Disk   > 85%  → warning  | > 95%  → critical
  Suspicious processes > 0 → warning

Design decisions:
  - `evaluate_thresholds` is called synchronously inside `ingest_metric`
    after a successful DB write. This keeps alert generation atomic
    with the metric ingestion.
  - Deduplication: if an unresolved alert of the same title already exists
    for the device, we skip creating a duplicate. This prevents flooding.
  - Alerts auto-resolve: when a metric drops back below the warning
    threshold the previously triggered alert is resolved automatically.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.metric import Metric
from app.repositories.alert_repository import alert_repository
from app.repositories.device_repository import device_repository
from app.schemas.alert import AlertCreate, AlertListResponse, AlertOut


# ── Threshold configuration ───────────────────────────────────────────────────
class Thresholds:
    CPU_WARNING: float = 75.0
    CPU_CRITICAL: float = 90.0
    RAM_WARNING: float = 75.0
    RAM_CRITICAL: float = 85.0
    DISK_WARNING: float = 80.0
    DISK_CRITICAL: float = 90.0



# ── Threshold engine ──────────────────────────────────────────────────────────
def evaluate_thresholds(db: Session, device_id: int, metric: Metric) -> List[Alert]:
    """
    Evaluates a freshly ingested metric against thresholds.
    Creates new alerts for violations and auto-resolves healed ones.

    Returns the list of newly created Alert objects.
    """
    created: List[Alert] = []

    checks = [
        # (metric_value, warning_threshold, critical_threshold, alert_title_prefix)
        (metric.cpu_usage_percent, Thresholds.CPU_WARNING, Thresholds.CPU_CRITICAL, "High CPU Usage"),
        (metric.ram_usage_percent, Thresholds.RAM_WARNING, Thresholds.RAM_CRITICAL, "High RAM Usage"),
        (metric.disk_usage_percent, Thresholds.DISK_WARNING, Thresholds.DISK_CRITICAL, "High Disk Usage"),
    ]

    for value, warn_thresh, crit_thresh, title_prefix in checks:
        if value is None:
            continue

        if value >= crit_thresh:
            severity = "critical"
        elif value >= warn_thresh:
            severity = "warning"
        else:
            # Below threshold — auto-resolve any existing unresolved alert of same type
            _auto_resolve(db, device_id, title_prefix)
            continue

        title = f"{title_prefix}: {value:.1f}%"
        if not _duplicate_exists(db, device_id, title_prefix):
            alert = Alert(
                device_id=device_id,
                metric_id=metric.id,
                severity=severity,
                title=title,
                message=(
                    f"{title_prefix} detected at {value:.1f}% "
                    f"({'critical' if severity == 'critical' else 'warning'} threshold: "
                    f"{crit_thresh if severity == 'critical' else warn_thresh}%)."
                ),
            )
            created.append(alert_repository.create(db, obj=alert))

    # Suspicious process check
    if metric.suspicious_process_count and metric.suspicious_process_count > 0:
        title = f"Suspicious Processes Detected: {metric.suspicious_process_count}"
        if not _duplicate_exists(db, device_id, "Suspicious Processes"):
            alert = Alert(
                device_id=device_id,
                metric_id=metric.id,
                severity="warning",
                title=title,
                message=(
                    f"{metric.suspicious_process_count} suspicious process(es) detected "
                    "on this endpoint. Review the process list immediately."
                ),
            )
            created.append(alert_repository.create(db, obj=alert))
    else:
        _auto_resolve(db, device_id, "Suspicious Processes")

    return created


def _duplicate_exists(db: Session, device_id: int, title_prefix: str) -> bool:
    """True if an unresolved alert with a matching title prefix already exists."""
    alerts = alert_repository.get_for_device(db, device_id, only_unresolved=True, limit=50)
    return any(title_prefix in a.title for a in alerts)


def _auto_resolve(db: Session, device_id: int, title_prefix: str) -> None:
    """Resolve any unresolved alerts whose title starts with title_prefix."""
    alerts = alert_repository.get_for_device(db, device_id, only_unresolved=True, limit=50)
    for alert in alerts:
        if title_prefix in alert.title:
            alert_repository.resolve(db, alert)


# ── CRUD operations (for the REST API) ───────────────────────────────────────
def create_alert(db: Session, payload: AlertCreate) -> Alert:
    """Manually create an alert for a device."""
    device = device_repository.get_by_uuid(db, payload.device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{payload.device_uuid}' not found.")
    alert = Alert(
        device_id=device.id,
        severity=payload.severity,
        title=payload.title,
        message=payload.message,
        metric_id=payload.metric_id,
    )
    return alert_repository.create(db, obj=alert)


def resolve_alert(db: Session, alert_id: int) -> Alert:
    """Resolve an alert by ID."""
    alert = alert_repository.get(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    if alert.is_resolved:
        raise HTTPException(status_code=400, detail="Alert is already resolved.")
    return alert_repository.resolve(db, alert)


def get_device_alerts(
    db: Session,
    device_uuid: str,
    only_unresolved: bool = False,
    limit: int = 100,
) -> AlertListResponse:
    """List alerts for a device."""
    device = device_repository.get_by_uuid(db, device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{device_uuid}' not found.")
    alerts = alert_repository.get_for_device(db, device.id, only_unresolved=only_unresolved, limit=limit)
    total = alert_repository.count_for_device(db, device.id)
    return AlertListResponse(device_id=device.id, total=total, alerts=alerts)


def get_user_unresolved_alerts(db: Session, user_id: int) -> List[Alert]:
    """Get all unresolved alerts across all devices owned by the given user."""
    return alert_repository.get_unresolved_for_user(db, user_id, limit=200)


def resolve_all_user_alerts(db: Session, user_id: int) -> int:
    """Resolve all active unresolved alerts for the given user."""
    return alert_repository.resolve_all_for_user(db, user_id)


def trigger_test_alert(
    db: Session,
    user_id: int,
    device_uuid: Optional[str] = None,
    alert_type: str = "suspicious_process",
) -> Alert:
    """
    Simulate a security anomaly / alert for testing real-time notifications.
    """
    from app.repositories.device_repository import device_repository
    user_devices = device_repository.get_all_by_user(db, user_id)
    if not user_devices:
        raise HTTPException(status_code=400, detail="No devices found for this user to trigger a test alert.")

    target_device = None
    if device_uuid:
        target_device = device_repository.get_by_uuid(db, device_uuid)
    if not target_device:
        target_device = user_devices[0]

    templates = {
        "suspicious_process": (
            "warning",
            "Suspicious Process Heuristic Triggered: temp_updater.pdf.exe",
            "Security Heuristic Warning: Unsigned binary running from %APPDATA%\\Local\\Temp with double extension (.pdf.exe). PID: 9842.",
        ),
        "high_cpu": (
            "critical",
            "Critical CPU Spike: 98.4%",
            "System CPU usage spiked to 98.4% across 8 cores. Potential crypto-mining process or runaway thread detected.",
        ),
        "high_memory": (
            "warning",
            "High RAM Memory Consumption: 91.2%",
            "System physical memory usage exceeded 90% (14.6 GB / 16.0 GB). Endpoint performance degraded.",
        ),
        "ransomware_heuristic": (
            "critical",
            "CRITICAL SECURITY ANOMALY: Mass File Encryption Activity",
            "Anomaly Engine Alert: Rapid file modification rate detected in C:\\Users\\Documents\\. Cryptographic ransomware behavioral signature flagged!",
        ),
    }

    severity, title, message = templates.get(
        alert_type,
        templates["suspicious_process"],
    )

    alert = Alert(
        device_id=target_device.id,
        severity=severity,
        title=title,
        message=message,
    )
    created = alert_repository.create(db, obj=alert)

    # Broadcast immediately to active WebSocket subscribers
    try:
        import asyncio
        from app.api.v1.endpoints.ws import ws_manager
        from app.core.event_loop import get_main_loop
        loop = get_main_loop()
        if loop and not loop.is_closed():
            alert_dict = {
                "type": "alert",
                "device_uuid": target_device.device_uuid,
                "id": created.id,
                "severity": created.severity,
                "title": created.title,
                "message": created.message,
                "is_resolved": created.is_resolved,
                "created_at": created.created_at.isoformat() if created.created_at else None,
            }
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(target_device.device_uuid, alert_dict),
                loop,
            )
    except Exception:
        pass

    return created

