"""Metric Repository — time-series query methods for device metrics."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.metric import Metric
from app.repositories.base_repository import BaseRepository


class MetricRepository(BaseRepository[Metric]):

    def __init__(self):
        super().__init__(Metric)

    def get_latest_for_device(self, db: Session, device_id: int) -> Optional[Metric]:
        """Return the single most recent metric snapshot for a device."""
        return (
            db.query(Metric)
            .filter(Metric.device_id == device_id)
            .order_by(desc(Metric.created_at))
            .first()
        )

    def get_history_for_device(
        self, db: Session, device_id: int, limit: int = 100
    ) -> List[Metric]:
        """Return the last N metric snapshots for a device, newest first."""
        return (
            db.query(Metric)
            .filter(Metric.device_id == device_id)
            .order_by(desc(Metric.created_at))
            .limit(limit)
            .all()
        )

    def get_by_device_count(self, db: Session, device_id: int) -> int:
        """Return total number of stored metric snapshots for a device."""
        return db.query(Metric).filter(Metric.device_id == device_id).count()


metric_repository = MetricRepository()
