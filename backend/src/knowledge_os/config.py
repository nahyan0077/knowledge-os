from functools import lru_cache

from pydantic import Field
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
    jwt_secret: str = Field(
        default="development-only-secret-change-before-deploy",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    secure_cookies: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
