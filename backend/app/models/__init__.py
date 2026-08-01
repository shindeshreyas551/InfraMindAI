"""SQLAlchemy ORM models package — imports here register all tables with Base.metadata."""

from app.models.user import User
from app.models.device import Device
from app.models.metric import Metric
from app.models.alert import Alert
from app.models.ai_analysis import AIAnalysis

__all__ = ["User", "Device", "Metric", "Alert", "AIAnalysis"]
