from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KNOWLEDGE_OS_",
        extra="ignore",
    )

    app_name: str = "Knowledge OS API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://knowledge_os:knowledge_os@localhost:5432/knowledge_os"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Normalizes postgres:// and postgresql:// to use the asyncpg driver
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    jwt_secret: str = Field(
        default="development-only-secret-change-before-deploy",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    secure_cookies: bool = False
    azure_storage_connection_string: str | None = None
    azure_storage_container_name: str = "documents"
    storage_provider: str = "azure_blob"  # "azure_blob", "google_gcs", or "local"
    google_application_credentials: str | None = None
    gcs_bucket_name: str = "documents"
    google_client_id: str | None = None

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_timeout: int = 10

    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    embedding_provider: str = "openai"  # "openai" or "gemini"

    model_pricing: dict[str, dict[str, float]] = {
        "gpt-4o-mini": {"input_rate_per_million": 0.150, "output_rate_per_million": 0.600},
        "gpt-4o": {"input_rate_per_million": 5.00, "output_rate_per_million": 15.00},
        "claude-3-5-sonnet": {"input_rate_per_million": 3.00, "output_rate_per_million": 15.00},
        "gemini-1.5-pro": {"input_rate_per_million": 1.25, "output_rate_per_million": 5.00},
        "gemini-1.5-flash": {"input_rate_per_million": 0.075, "output_rate_per_million": 0.30},
        "default": {"input_rate_per_million": 0.150, "output_rate_per_million": 0.600},
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
