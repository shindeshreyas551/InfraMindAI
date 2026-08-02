"""Pydantic schemas for Device registration, heartbeat, and API responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeviceRegister(BaseModel):
    """Payload sent by the agent on startup to register or re-register itself."""
    device_uuid: str = Field(..., description="Persistent UUID from agent's .device_id file")
    hostname: str
    display_name: Optional[str] = None
    os_name: str = Field(default="Windows")
    os_version: str = Field(default="")
    architecture: str = Field(default="")
    agent_version: str = Field(default="0.0.0")
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None


class DeviceHeartbeat(BaseModel):
    """Payload for POST /devices/{device_uuid}/heartbeat."""
    device_uuid: str


class DeviceUpdate(BaseModel):
    """Payload for PATCH /devices/{device_uuid} to update metadata / rename."""
    display_name: Optional[str] = None
    hostname: Optional[str] = None


class DeviceOut(BaseModel):
    """Device representation returned by the API."""
    id: int
    device_uuid: str
    hostname: str
    display_name: Optional[str] = None
    os_name: str
    os_version: str
    architecture: str
    agent_version: str
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    is_online: bool
    is_disabled: bool = False
    last_seen_at: Optional[datetime]
    registered_at: datetime
    owner_id: Optional[int]

    model_config = {"from_attributes": True}
