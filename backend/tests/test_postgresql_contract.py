import os
import sys
from pathlib import Path

from sqlalchemy import ForeignKeyConstraint

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Settings, normalize_database_url  # noqa: E402
from db.models import Base  # noqa: E402


def test_runtime_url_normalization_preserves_secret_and_selects_psycopg():
    value = "postgresql://user:secret@example.neon.tech/neondb?sslmode=require"
    normalized = normalize_database_url(value)
    assert normalized.startswith("postgresql+psycopg://")
    assert "secret" in normalized
    assert "example.neon.tech" in normalized


def test_production_migration_guard_defaults_closed():
    settings = Settings(
        database_url="postgresql://user:secret@example.neon.tech/db",
        database_target="production",
    )
    assert settings.allow_production_migrations is False


def test_initial_schema_has_expected_tables_and_user_foreign_keys():
    expected = {
        "users",
        "user_sessions",
        "documents",
        "extracted_tables",
        "pdf_files",
        "google_tokens",
        "oauth_states",
    }
    assert expected.issubset(Base.metadata.tables)
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and "users.user_id" in str(constraint.elements[0].target_fullname)
        for constraint in Base.metadata.tables["documents"].constraints
        if isinstance(constraint, ForeignKeyConstraint)
    )
    assert "user_id" in Base.metadata.tables["extracted_tables"].c
    assert "data" in Base.metadata.tables["pdf_files"].c


def test_postgres_integration_requires_explicit_production_connection():
    """The live Neon suite is opt-in and must never silently use SQLite."""
    database_url = os.environ.get("DATABASE_URL", "")
    assert not database_url or database_url.startswith(
        ("postgresql://", "postgres://", "postgresql+psycopg://")
    )
