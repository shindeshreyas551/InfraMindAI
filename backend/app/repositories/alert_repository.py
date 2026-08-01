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


alert_repository = AlertRepository()
