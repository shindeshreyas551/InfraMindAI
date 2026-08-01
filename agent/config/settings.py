"""
InfraMind AI - Settings & Environment Configuration Management
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


AGENT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = AGENT_DIR / ".env"


class AgentSettings(BaseSettings):
    """Pydantic BaseSettings class loading parameters from .env file."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    agent_name: str = "InfraMind-Windows-Agent"
    agent_version: str = "0.2.0"
    backend_url: str = "http://localhost:8000/api/v1/telemetry"
    collection_interval_sec: float = 10.0
    log_level: str = "INFO"
    log_file_path: str = "logs/agent.log"
    max_log_bytes: int = 5_242_880  # 5 MB
    backup_count: int = 3

    # Feature Toggles
    collect_cpu: bool = True
    collect_memory: bool = True
    collect_disk: bool = True
    collect_network: bool = True
    collect_system: bool = True
    collect_battery: bool = True
    collect_processes: bool = True
    max_processes_to_collect: int = 15
    cpu_sample_interval_sec: float = 1.0

    # ── Backend API Connection ────────────────────────────────────────────────
    backend_api_url: str = "http://localhost:8000/api/v1"
    backend_email: str = "admin@inframind.ai"
    backend_password: str = "SecurePass123"
    upload_interval_sec: float = 5.0     # How often the agent POSTs telemetry
    upload_timeout_sec: float = 10.0     # HTTP request timeout
    upload_max_retries: int = 3          # Retry attempts per failed upload
    offline_queue_max_size: int = 100    # Max queued payloads when backend is down


    @property
    def absolute_log_file_path(self) -> Path:
        """Returns resolved absolute Path for log file."""
        log_p = Path(self.log_file_path)
        if not log_p.is_absolute():
            log_p = AGENT_DIR / log_p
        log_p.parent.mkdir(parents=True, exist_ok=True)
        return log_p


# Global settings instance
get_settings = AgentSettings()
