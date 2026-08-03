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
from app.schemas.device import DeviceRegister, DeviceOut, DeviceUpdate
from app.services.device_service import (
    register_or_update_device,
    process_heartbeat,
    get_all_devices,
    get_device_by_uuid,
    update_device,
    delete_device,
    toggle_disable_device,
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
    return get_all_devices(db, owner_id=current_user.id)


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
    return get_device_by_uuid(db, device_uuid, owner_id=current_user.id)


@router.patch(
    "/{device_uuid}",
    response_model=DeviceOut,
    summary="Rename or update device display name",
)
def rename(
    device_uuid: str,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename a device's display_name or hostname."""
    updates = payload.model_dump(exclude_unset=True)
    return update_device(db, device_uuid, updates, owner_id=current_user.id)


@router.delete(
    "/{device_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a device from monitoring",
)
def remove(
    device_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a device and cascade remove its historical metrics and alerts."""
    delete_device(db, device_uuid, owner_id=current_user.id)
    return None


@router.post(
    "/{device_uuid}/toggle-disable",
    response_model=DeviceOut,
    summary="Disable or enable endpoint monitoring",
)
def toggle_disable(
    device_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggles endpoint monitoring state between enabled and disabled."""
    return toggle_disable_device(db, device_uuid, owner_id=current_user.id)
