"""
API v1 Router — aggregates all endpoint routers under /api/v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.devices import router as devices_router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.ws import router as ws_router
from app.api.v1.endpoints.download import router as download_router
from app.api.v1.endpoints.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(devices_router)
api_router.include_router(metrics_router)
api_router.include_router(alerts_router)
api_router.include_router(ws_router)
api_router.include_router(download_router)
api_router.include_router(admin_router)
