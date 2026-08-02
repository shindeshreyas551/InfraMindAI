"""
Core Configuration Settings for InfraMind AI FastAPI Backend
"""

from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application Settings Schema."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "InfraMind AI Backend API"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 1 day
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    DATABASE_URL: str
    RATE_LIMIT_PER_MINUTE: int = 10  # Per-IP rate limit on sensitive endpoints

    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("DATABASE_URL", mode="before")
    def validate_and_format_database_url(cls, v: Union[str, None]) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError(
                "DATABASE_URL environment variable is missing or empty. "
                "A valid PostgreSQL connection string is required for production."
            )
        v = v.strip()
        # Automatically convert legacy postgres:// protocol to postgresql:// for SQLAlchemy compatibility
        if v.startswith("postgres://"):
            v = "postgresql://" + v[11:]
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str], None]) -> List[str]:
        if not v:
            return ["*"]
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str or v_str == "*":
                return ["*"]
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [i.strip() for i in v_str.split(",") if i.strip()]
        return v



settings = Settings()

