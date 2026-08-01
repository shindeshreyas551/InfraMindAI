"""Repositories package — exposes singleton repository instances."""

from app.repositories.user_repository import user_repository
from app.repositories.device_repository import device_repository
from app.repositories.metric_repository import metric_repository

__all__ = ["user_repository", "device_repository", "metric_repository"]
