"""Device Repository — lookup methods specific to the Device model."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.device import Device
from app.repositories.base_repository import BaseRepository


class DeviceRepository(BaseRepository[Device]):

    def __init__(self):
        super().__init__(Device)

    def get_by_uuid(self, db: Session, device_uuid: str) -> Optional[Device]:
        """Fetch a device by its agent-generated persistent UUID."""
        return db.query(Device).filter(Device.device_uuid == device_uuid).first()

    def get_by_owner(self, db: Session, owner_id: int) -> List[Device]:
        """Return all devices belonging to a specific user."""
        return db.query(Device).filter(Device.owner_id == owner_id).all()

    def update_heartbeat(self, db: Session, device: Device, is_online: bool = True) -> Device:
        """Update last_seen_at and is_online status for a heartbeat ping."""
        device.last_seen_at = datetime.now(timezone.utc)
        device.is_online = is_online
        db.add(device)
        db.commit()
        db.refresh(device)
        return device

    def mark_offline(self, db: Session, device: Device) -> Device:
        """Mark a device as offline (used by a background timeout checker)."""
        return self.update_heartbeat(db, device, is_online=False)


device_repository = DeviceRepository()
