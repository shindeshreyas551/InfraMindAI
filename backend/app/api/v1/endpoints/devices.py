"""
Device API endpoints.

Routes:
  POST /api/v1/devices/register           → register or update device
  POST /api/v1/devices/{uuid}/heartbeat   → update last-seen timestamp
  GET  /api/v1/devices/                   → list devices (auth required)
  GET  /api/v1/devices/{uuid}             → get single device detail (auth required)
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.device import DeviceRegister, DeviceOut
from app.services.device_service import (
    register_or_update_device,
    process_heartbeat,
    get_all_devices,
    get_device_by_uuid,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post(
    "/register",
    response_model=DeviceOut,
    status_code=status.HTTP_200_OK,
    summary="Register or update a monitored device",
)
def register_device(
    payload: DeviceRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called by the Windows agent on startup.
    Idempotent — re-registering an existing device_uuid updates its metadata.
    """
    return register_or_update_device(db, payload, owner_id=current_user.id)


@router.post(
    "/{device_uuid}/heartbeat",
    response_model=DeviceOut,
    summary="Send a heartbeat to update device online status",
)
def heartbeat(
    device_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agent sends this every N seconds to keep the device marked as online."""
    return process_heartbeat(db, device_uuid)


@router.get(
    "/",
    response_model=List[DeviceOut],
    summary="List all devices owned by the current user",
)
def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all devices registered under the authenticated user account."""
    owner_id = None if current_user.is_superuser else current_user.id
    return get_all_devices(db, owner_id=owner_id)


@router.get(
    "/{device_uuid}",
    response_model=DeviceOut,
    summary="Get device details by UUID",
)
def get_device(
    device_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch full details for a single device by its agent UUID."""
    return get_device_by_uuid(db, device_uuid)
