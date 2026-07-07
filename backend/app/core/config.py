from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "IRDoc"
    BASE_URL: AnyHttpUrl = "http://localhost:3000"  # type: ignore[assignment]
    ALLOW_REGISTRATION: bool = True
    VERSION: str = "dev"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://irp:changeme@db/irp"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str = "CHANGE_ME_generate_with_openssl_rand_hex_32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    COOKIE_SECURE: bool = False

    # Storage
    STORAGE_BACKEND: Literal["local", "s3", "azure_blob", "gcs"] = "local"
    STORAGE_PATH: str = "/app/storage"

    # License
    LICENSE_KEY: str = ""

    # Webhook
    WEBHOOK_RATE_LIMIT: int = 20
    WEBHOOK_MAX_PAYLOAD_BYTES: int = 65536

    # AI (Phase 3)
    AI_BACKEND: Literal["anthropic", "openai", "ollama"] = "anthropic"
    AI_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://ollama:11434"

    # MSSP
    MSSP_MODE: bool = False

    # CORS — defaults to BASE_URL; override for multi-origin setups
    CORS_ORIGINS: list[str] = []

    @field_validator("SECRET_KEY")
    @classmethod
    def require_real_secret(cls, v: str) -> str:
        if v == "CHANGE_ME_generate_with_openssl_rand_hex_32" or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be set to a cryptographically random value "
                "(openssl rand -hex 32). Refusing to start with the default."
            )
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def get_cors_origins(self) -> list[str]:
        if self.CORS_ORIGINS:
            return self.CORS_ORIGINS
        return [str(self.BASE_URL).rstrip("/")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
