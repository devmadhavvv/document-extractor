"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API service."""

    service_name: str = "AI Onboarding Document Extraction API"
    environment: str = "development"
    api_prefix: str = ""
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )
    firebase_project_id: str | None = None
    firebase_credentials_path: str | None = None
    firebase_storage_bucket: str | None = None
    upload_temp_dir: str = "temp"
    max_upload_size_bytes: int = 10 * 1024 * 1024
    cleanup_max_age_hours: float = 1
    cleanup_interval_seconds: int = 3600
    frontend_dist_dir: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_request_timeout_seconds: float = 60.0
    gemini_max_retries: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str] | None) -> list[str] | None:
        """Support comma-separated CORS origins from environment variables."""
        if value is None or isinstance(value, list):
            return value

        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
