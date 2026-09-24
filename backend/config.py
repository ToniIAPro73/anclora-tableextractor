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
    google_auth_client_id: str = ""
    google_auth_client_secret: str = ""
    google_auth_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_auth_redirect_uri: str = "http://localhost:8000/api/auth/github/callback"
    auth_admin_emails: str = ""
    auth_invitation_ttl_hours: int = 72
    auth_password_min_length: int = 12
    google_client_id: str = ""
    google_client_secret: str = ""
    google_sheets_redirect_uri: str = ""
    llm_provider: str = "disabled"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o-mini"
    object_storage_backend: str = "database"
    object_storage_endpoint_url: str = ""
    object_storage_region: str = ""
    object_storage_bucket: str = ""
    object_storage_access_key_id: str = ""
    object_storage_secret_access_key: str = ""
    database_pdf_max_bytes: int = 15_000_000

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
