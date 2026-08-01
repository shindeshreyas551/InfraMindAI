"""
Device Identity Manager for InfraMind AI Windows Agent
"""

import uuid
from pathlib import Path
from agent.config.settings import AGENT_DIR


DEVICE_ID_FILE = AGENT_DIR / ".device_id"


class DeviceIdentityManager:
    """
    Manages persistent unique device identification across agent restarts.
    Generates UUID4 on first run and persists to local disk file.
    """

    def __init__(self, identity_file: Path = DEVICE_ID_FILE):
        self.identity_file = identity_file

    def get_or_create_device_id(self) -> str:
        """
        Retrieves existing Device ID from local disk storage,
        or creates a new UUID4 Device ID if one does not exist.
        
        :return: String UUID4 representing device identity.
        """
        if self.identity_file.exists():
            try:
                device_id = self.identity_file.read_text(encoding="utf-8").strip()
                if device_id:
                    return device_id
            except Exception:
                pass  # Fall through to re-generate if file is corrupted

        # Generate new persistent UUID
        new_device_id = f"dev_{uuid.uuid4().hex}"
        self.identity_file.write_text(new_device_id, encoding="utf-8")
        return new_device_id
