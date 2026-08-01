"""
Device Service — register_or_update, heartbeat, and listing logic.

Design decisions:
  - `register_or_update_device` is idempotent: if the agent restarts it simply
    updates the existing record rather than creating a duplicate. The agent's
    persistent device_uuid is the natural key.
  - Devices can optionally be linked to a user (owner_id). If the agent sends
    an authenticated request the device is claimed; unauthenticated agents
    create unowned devices that can be adopted later.
  - Heartbeat updates `last_seen_at` and flips `is_online` to True.
"""

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.device import Device
from app.repositories.device_repository import device_repository
from app.schemas.device import DeviceRegister


def register_or_update_device(
    db: Session,
    payload: DeviceRegister,
    owner_id: Optional[int] = None,
) -> Device:
    """
    Register a new device or update an existing one.
    Uses device_uuid as the idempotency key.
    """
    existing = device_repository.get_by_uuid(db, payload.device_uuid)

    if existing:
        # Update mutable fields on re-registration
        updates = {
            "hostname": payload.hostname,
            "os_name": payload.os_name,
            "os_version": payload.os_version,
            "architecture": payload.architecture,
            "agent_version": payload.agent_version,
        }
        if owner_id and existing.owner_id is None:
            updates["owner_id"] = owner_id
        device = device_repository.update(db, db_obj=existing, updates=updates)
    else:
        device = Device(
            device_uuid=payload.device_uuid,
            hostname=payload.hostname,
            os_name=payload.os_name,
            os_version=payload.os_version,
            architecture=payload.architecture,
            agent_version=payload.agent_version,
            owner_id=owner_id,
        )
        device = device_repository.create(db, obj=device)

    # Mark online immediately after registration
    return device_repository.update_heartbeat(db, device, is_online=True)


def process_heartbeat(db: Session, device_uuid: str) -> Device:
    """Update the device's last_seen_at and ensure it is marked online."""
    device = device_repository.get_by_uuid(db, device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_uuid}' is not registered.",
        )
    return device_repository.update_heartbeat(db, device, is_online=True)


def get_all_devices(db: Session, owner_id: Optional[int] = None) -> List[Device]:
    """Return devices filtered by owner, or all devices for superusers."""
    if owner_id is not None:
        return device_repository.get_by_owner(db, owner_id)
    return device_repository.get_multi(db, limit=200)


def get_device_by_uuid(db: Session, device_uuid: str) -> Device:
    """Fetch a single device by UUID or raise 404."""
    device = device_repository.get_by_uuid(db, device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_uuid}' not found.",
        )
    return device
