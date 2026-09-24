from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, BYTEA
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    name: Mapped[str] = mapped_column(Text, default="", nullable=False)
    picture: Mapped[Optional[str]] = mapped_column(Text)
    is_test_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserSessionRow(Base):
    __tablename__ = "user_sessions"
    session_token: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PasswordCredentialRow(Base):
    __tablename__ = "password_credentials"
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OAuthIdentityRow(Base):
    __tablename__ = "oauth_identities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_subject: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_oauth_identity_provider_subject"),)


class InvitationRow(Base):
    __tablename__ = "auth_invitations"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthAuditRow(Base):
    __tablename__ = "auth_audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(Text, index=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DocumentRow(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(Text, default="pendiente", nullable=False)
    num_paginas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_tablas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    process_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    thumb_path: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_documents_user_fecha", "user_id", "fecha_carga"),)


class ExtractedTableRow(Base):
    __tablename__ = "extracted_tables"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    documento_id: Mapped[str] = mapped_column(
        Text, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pagina_origen: Mapped[int] = mapped_column(Integer, nullable=False)
    source_pages: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    extraction_method: Mapped[str] = mapped_column(
        Text, default="native", nullable=False
    )
    columnas: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    column_types: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    num_filas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_columnas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cells: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    column_rules: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_extracted_tables_user_document", "user_id", "documento_id"),
    )


class PdfFileRow(Base):
    __tablename__ = "pdf_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    documento_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    storage_path: Mapped[Optional[str]] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(
        Text, default="application/pdf", nullable=False
    )
    size: Mapped[Optional[int]] = mapped_column(BigInteger)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    data: Mapped[Optional[bytes]] = mapped_column(BYTEA)


class GoogleTokenRow(Base):
    __tablename__ = "google_tokens"
    user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    token_uri: Mapped[Optional[str]] = mapped_column(Text)
    client_id: Mapped[Optional[str]] = mapped_column(Text)
    client_secret: Mapped[Optional[str]] = mapped_column(Text)
    scopes: Mapped[Optional[list[Any]]] = mapped_column(JSONB)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OAuthStateRow(Base):
    __tablename__ = "oauth_states"
    state: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_id: Mapped[str] = mapped_column(
        Text, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
