"""Closed registration, password credentials, social identities and audit."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_auth_access_control"
down_revision = "0001_initial_postgresql_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("status", sa.Text(), nullable=False, server_default="active"))
    op.create_table(
        "password_credentials",
        sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "oauth_identities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_subject", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_oauth_identity_provider_subject"),
    )
    op.create_index("ix_oauth_identities_user_id", "oauth_identities", ["user_id"])
    op.create_table(
        "auth_invitations",
        sa.Column("id", sa.Text(), primary_key=True), sa.Column("email", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auth_invitations_email", "auth_invitations", ["email"])
    op.create_index("ix_auth_invitations_expires_at", "auth_invitations", ["expires_at"])
    op.create_table(
        "auth_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True), sa.Column("event", sa.Text(), nullable=False),
        sa.Column("email", sa.Text()), sa.Column("user_id", sa.Text()), sa.Column("ip_hash", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auth_audit_events_email", "auth_audit_events", ["email"])
    op.create_index("ix_auth_audit_events_user_id", "auth_audit_events", ["user_id"])


def downgrade() -> None:
    op.drop_table("auth_audit_events")
    op.drop_table("auth_invitations")
    op.drop_table("oauth_identities")
    op.drop_table("password_credentials")
    op.drop_column("users", "status")
