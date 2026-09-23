"""Initial PostgreSQL schema for TableExtract."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_postgresql_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("user_id", sa.Text(), primary_key=True), sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False, server_default=""), sa.Column("picture", sa.Text()),
        sa.Column("is_test_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("user_sessions",
        sa.Column("session_token", sa.Text(), primary_key=True), sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table("documents",
        sa.Column("id", sa.Text(), primary_key=True), sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nombre_archivo", sa.Text(), nullable=False), sa.Column("estado", sa.Text(), nullable=False, server_default="pendiente"),
        sa.Column("num_paginas", sa.Integer(), nullable=False, server_default="0"), sa.Column("num_tablas", sa.Integer(), nullable=False, server_default="0"), sa.Column("process_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thumb_path", sa.Text()), sa.Column("error", sa.Text()), sa.Column("fecha_carga", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_user_fecha", "documents", ["user_id", "fecha_carga"])
    jsonb = postgresql.JSONB()
    op.create_table("extracted_tables",
        sa.Column("id", sa.Text(), primary_key=True), sa.Column("documento_id", sa.Text(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False), sa.Column("pagina_origen", sa.Integer(), nullable=False),
        sa.Column("source_pages", jsonb, nullable=False, server_default="[]"), sa.Column("extraction_method", sa.Text(), nullable=False, server_default="native"), sa.Column("columnas", jsonb, nullable=False, server_default="[]"), sa.Column("column_types", jsonb, nullable=False, server_default="[]"),
        sa.Column("num_filas", sa.Integer(), nullable=False, server_default="0"), sa.Column("num_columnas", sa.Integer(), nullable=False, server_default="0"), sa.Column("cells", jsonb, nullable=False, server_default="[]"), sa.Column("column_rules", jsonb, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_extracted_tables_documento_id", "extracted_tables", ["documento_id"])
    op.create_index("ix_extracted_tables_user_id", "extracted_tables", ["user_id"])
    op.create_index("ix_extracted_tables_user_document", "extracted_tables", ["user_id", "documento_id"])
    op.create_table("pdf_files",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("documento_id", sa.Text(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False), sa.Column("storage_path", sa.Text()), sa.Column("original_filename", sa.Text(), nullable=False), sa.Column("content_type", sa.Text(), nullable=False, server_default="application/pdf"), sa.Column("size", sa.BigInteger()), sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("data", sa.LargeBinary()), sa.UniqueConstraint("documento_id", name="uq_pdf_files_documento_id"),
    )
    op.create_index("ix_pdf_files_documento_id", "pdf_files", ["documento_id"])
    op.create_index("ix_pdf_files_user_id", "pdf_files", ["user_id"])
    op.create_table("google_tokens",
        sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True), sa.Column("access_token", sa.Text()), sa.Column("refresh_token", sa.Text()), sa.Column("token_uri", sa.Text()), sa.Column("client_id", sa.Text()), sa.Column("client_secret", sa.Text()), sa.Column("scopes", jsonb), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table("oauth_states",
        sa.Column("state", sa.Text(), primary_key=True), sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False), sa.Column("doc_id", sa.Text(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_oauth_states_user_id", "oauth_states", ["user_id"])


def downgrade() -> None:
    op.drop_table("oauth_states")
    op.drop_table("google_tokens")
    op.drop_table("pdf_files")
    op.drop_table("extracted_tables")
    op.drop_table("documents")
    op.drop_table("user_sessions")
    op.drop_table("users")
