"""Alert Repository — query methods specific to the Alert model."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.alert import Alert
from app.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[Alert]):

    def __init__(self):
        super().__init__(Alert)

    def get_for_device(
        self,
        db: Session,
        device_id: int,
        only_unresolved: bool = False,
        limit: int = 100,
    ) -> List[Alert]:
        """Return alerts for a device, newest first. Optionally filter unresolved."""
        q = db.query(Alert).filter(Alert.device_id == device_id)
        if only_unresolved:
            q = q.filter(Alert.is_resolved == False)  # noqa: E712
        return q.order_by(desc(Alert.created_at)).limit(limit).all()

    def get_unresolved_count(self, db: Session, device_id: int) -> int:
        """Count unresolved alerts for a device."""
        return (
            db.query(Alert)
            .filter(Alert.device_id == device_id, Alert.is_resolved == False)  # noqa: E712
            .count()
        )

    def resolve(self, db: Session, alert: Alert) -> Alert:
        """Mark an alert as resolved and set resolved_at timestamp."""
        alert.is_resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    def count_for_device(self, db: Session, device_id: int) -> int:
        """Total alert count for a device."""
        return db.query(Alert).filter(Alert.device_id == device_id).count()

    def get_unresolved_for_user(self, db: Session, user_id: int, limit: int = 100) -> List[Alert]:
        """Return all unresolved alerts for devices owned by the given user."""
        from app.models.device import Device
        return (
            db.query(Alert)
            .join(Device, Alert.device_id == Device.id)
            .filter(Device.owner_id == user_id, Alert.is_resolved == False)  # noqa: E712
            .order_by(desc(Alert.created_at))
            .limit(limit)
            .all()
        )

    def resolve_all_for_user(self, db: Session, user_id: int) -> int:
        """Resolve all unresolved alerts for devices owned by user. Returns count resolved."""
        alerts = self.get_unresolved_for_user(db, user_id, limit=500)
        count = 0
        now = datetime.now(timezone.utc)
        for alert in alerts:
            alert.is_resolved = True
            alert.resolved_at = now
            db.add(alert)
            count += 1
        db.commit()
        return count


alert_repository = AlertRepository()

