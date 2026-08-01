"""Pydantic schemas for Device registration, heartbeat, and API responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeviceRegister(BaseModel):
    """Payload sent by the agent on startup to register or re-register itself."""
    device_uuid: str = Field(..., description="Persistent UUID from agent's .device_id file")
    hostname: str
    os_name: str = Field(default="Windows")
    os_version: str = Field(default="")
    architecture: str = Field(default="")
    agent_version: str = Field(default="0.0.0")


class DeviceHeartbeat(BaseModel):
    """Payload for POST /devices/{device_uuid}/heartbeat."""
    device_uuid: str


class DeviceOut(BaseModel):
    """Device representation returned by the API."""
    id: int
    device_uuid: str
    hostname: str
    os_name: str
    os_version: str
    architecture: str
    agent_version: str
    is_online: bool
    last_seen_at: Optional[datetime]
    registered_at: datetime
    owner_id: Optional[int]

    model_config = {"from_attributes": True}
