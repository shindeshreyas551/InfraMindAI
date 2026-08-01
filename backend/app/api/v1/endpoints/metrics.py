"""
Metrics API endpoints.

Security:
  - POST /ingest validates Content-Length to prevent oversized payloads.
  - All routes require JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.metric import MetricIngest, MetricOut, MetricHistoryResponse
from app.services.metric_service import ingest_metric, get_latest_metric, get_metric_history
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/metrics", tags=["Metrics"])

# Maximum allowed payload size: 512 KB
_MAX_INGEST_BYTES = 512 * 1024


@router.post(
    "/ingest",
    response_model=MetricOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest telemetry payload from a Windows agent",
)
def ingest(
    request: Request,
    payload: MetricIngest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called by the Windows agent every 5 seconds.
    Validates payload size, stores indexed columns and full raw JSON.
    """
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_INGEST_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Payload too large. Maximum allowed size is {_MAX_INGEST_BYTES // 1024} KB.",
        )
    return ingest_metric(db, payload)


@router.get(
    "/{device_uuid}/latest",
    response_model=MetricOut,
    summary="Get the most recent metric snapshot for a device",
)
def latest(
    device_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the single most recent telemetry snapshot for the given device."""
    return get_latest_metric(db, device_uuid)


@router.get(
    "/{device_uuid}/history",
    response_model=MetricHistoryResponse,
    summary="Get paginated metric history for a device",
)
def history(
    device_uuid: str,
    limit: int = Query(default=100, ge=1, le=500, description="Number of snapshots (max 500)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the last N telemetry snapshots for a device (newest first)."""
    return get_metric_history(db, device_uuid, limit=limit)
