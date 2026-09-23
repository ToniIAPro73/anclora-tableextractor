from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = ""
    database_url_unpooled: str = ""
    database_target: str = "production"
    allow_production_migrations: bool = False
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    qa_user_email: str = "qa.tableextract@anclora.local"
    local_qa_login_enabled: bool = False
    local_qa_login_token: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_sheets_redirect_uri: str = ""
    emergent_llm_key: str = ""
    integration_proxy_url: str = ""
    emergent_object_storage_url: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors(cls, value: str | list[str]) -> str:
        if isinstance(value, list):
            return ",".join(value)
        return str(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    @property
    def runtime_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required")
        return normalize_database_url(self.database_url)

    @property
    def migration_database_url(self) -> str:
        return normalize_database_url(self.database_url_unpooled or self.database_url)


def normalize_database_url(value: str) -> str:
    if not value:
        return value
    if value.startswith("postgresql+psycopg://"):
        return value
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env == "production" and settings.local_qa_login_enabled:
        raise RuntimeError("LOCAL_QA_LOGIN_ENABLED cannot be true in production")
    return settings
