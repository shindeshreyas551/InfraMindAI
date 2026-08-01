"""
Alerts API endpoints.

Routes:
  GET  /api/v1/alerts/{device_uuid}           → list alerts for a device
  POST /api/v1/alerts/                        → manually create an alert
  POST /api/v1/alerts/{alert_id}/resolve      → resolve an alert
  GET  /api/v1/alerts/{device_uuid}/unresolved → unresolved alerts only
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertOut, AlertListResponse
from app.services.alert_service import (
    create_alert,
    resolve_alert,
    get_device_alerts,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "/{device_uuid}",
    response_model=AlertListResponse,
    summary="List all alerts for a device",
)
def list_alerts(
    device_uuid: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all alerts for the given device (resolved and unresolved), newest first."""
    return get_device_alerts(db, device_uuid, only_unresolved=False, limit=limit)


@router.get(
    "/{device_uuid}/unresolved",
    response_model=AlertListResponse,
    summary="List only unresolved alerts for a device",
)
def list_unresolved(
    device_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns only active (unresolved) alerts for the given device."""
    return get_device_alerts(db, device_uuid, only_unresolved=True, limit=200)


@router.post(
    "/",
    response_model=AlertOut,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create an alert for a device",
)
def create(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually raise an alert against a device (e.g. from dashboard or external system)."""
    return create_alert(db, payload)


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertOut,
    summary="Resolve an alert by ID",
)
def resolve(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an alert as resolved. Sets resolved_at timestamp automatically."""
    return resolve_alert(db, alert_id)
