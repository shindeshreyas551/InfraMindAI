"""
WebSocket endpoint for real-time metric streaming.

Design:
  - GET /ws/metrics/{device_uuid}?token=<JWT>
    Clients connect and receive a new metric JSON every time the agent pushes one.
  - ConnectionManager tracks active subscribers per device_uuid.
  - The metric_service calls `ws_manager.broadcast(device_uuid, data)` after
    each successful ingest — no polling, pure push.
  - JWT is passed as a query parameter (browsers cannot set WS headers).
  - Stale connections are detected via send failures and removed automatically.
"""

import json
import asyncio
import logging
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError

from app.core.security import decode_token
from app.core.database import SessionLocal
from app.repositories.user_repository import user_repository

logger = logging.getLogger("api.websocket")

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by device_uuid.
    Thread-safe for asyncio single-threaded event loop.
    """

    def __init__(self):
        # device_uuid → list of connected WebSocket clients
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, device_uuid: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(device_uuid, []).append(websocket)
        logger.info(f"WS client connected for device {device_uuid} "
                    f"(total={len(self._connections[device_uuid])})")

    def disconnect(self, device_uuid: str, websocket: WebSocket) -> None:
        clients = self._connections.get(device_uuid, [])
        if websocket in clients:
            clients.remove(websocket)
        if not clients:
            self._connections.pop(device_uuid, None)
        logger.info(f"WS client disconnected from device {device_uuid}")

    async def broadcast(self, device_uuid: str, data: dict) -> None:
        """
        Send a JSON payload to all subscribers of device_uuid.
        Stale / closed connections are removed silently.
        """
        clients = self._connections.get(device_uuid, [])
        if not clients:
            return

        dead: List[WebSocket] = []
        payload = json.dumps(data, default=str)

        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(device_uuid, ws)

    def active_devices(self) -> List[str]:
        """Return list of device UUIDs with at least one active subscriber."""
        return list(self._connections.keys())

    def subscriber_count(self, device_uuid: str) -> int:
        return len(self._connections.get(device_uuid, []))


# Global singleton — imported by metric_service to broadcast on ingest
ws_manager = ConnectionManager()


def _authenticate_ws_token(token: str) -> bool:
    """Validate a JWT access token. Returns True if valid."""
    db = None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return False
        user_id = int(payload["sub"])
        db = SessionLocal()
        user = user_repository.get(db, user_id)
        return user is not None and user.is_active
    except Exception:
        return False
    finally:
        if db is not None:
            db.close()


@router.websocket("/metrics/{device_uuid}")
async def ws_live_metrics(
    websocket: WebSocket,
    device_uuid: str,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint that streams live metric snapshots for a device.

    Connect: ws://localhost:8000/ws/metrics/{device_uuid}?token=<access_token>

    Receives: JSON metric snapshot pushed by the agent every 5 seconds.
    Sends:    heartbeat ping every 30s to keep the connection alive.
    """
    # Validate token before accepting
    if not _authenticate_ws_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(f"WS connection rejected for device {device_uuid} — invalid token")
        return

    await ws_manager.connect(device_uuid, websocket)

    try:
        # Keep connection alive — send heartbeat pings every 30s
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(device_uuid, websocket)
