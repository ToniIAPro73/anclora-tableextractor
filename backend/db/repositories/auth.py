from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuthAuditRow, InvitationRow, OAuthIdentityRow, PasswordCredentialRow


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def set_password(session: AsyncSession, user_id: str, password_hash: str) -> None:
    row = await session.get(PasswordCredentialRow, user_id)
    if row is None:
        session.add(PasswordCredentialRow(user_id=user_id, password_hash=password_hash))
    else:
        row.password_hash = password_hash
    await session.flush()


async def get_password(session: AsyncSession, user_id: str) -> Optional[PasswordCredentialRow]:
    return await session.get(PasswordCredentialRow, user_id)


async def create_invitation(session: AsyncSession, *, email: str, created_by: str, ttl_hours: int = 72) -> tuple[InvitationRow, str]:
    raw = secrets.token_urlsafe(32)
    row = InvitationRow(id=f"inv_{secrets.token_hex(12)}", email=normalize_email(email), token_hash=hash_token(raw), expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours), created_by=created_by)
    session.add(row)
    await session.flush()
    return row, raw


async def get_invitation(session: AsyncSession, raw_token: str) -> Optional[InvitationRow]:
    row = await session.scalar(select(InvitationRow).where(InvitationRow.token_hash == hash_token(raw_token)))
    if not row or row.revoked_at or row.accepted_at or row.expires_at <= datetime.now(timezone.utc):
        return None
    return row


async def get_active_invitation_for_email(session: AsyncSession, email: str) -> Optional[InvitationRow]:
    row = await session.scalar(select(InvitationRow).where(InvitationRow.email == normalize_email(email), InvitationRow.accepted_at.is_(None), InvitationRow.revoked_at.is_(None)))
    if not row or row.expires_at <= datetime.now(timezone.utc):
        return None
    return row


async def revoke_invitation(session: AsyncSession, invitation_id: str) -> None:
    await session.execute(update(InvitationRow).where(InvitationRow.id == invitation_id).values(revoked_at=datetime.now(timezone.utc)))


async def get_identity(session: AsyncSession, provider: str, subject: str) -> Optional[OAuthIdentityRow]:
    return await session.scalar(select(OAuthIdentityRow).where(OAuthIdentityRow.provider == provider, OAuthIdentityRow.provider_subject == subject))


async def link_identity(session: AsyncSession, *, user_id: str, provider: str, subject: str, email: str) -> OAuthIdentityRow:
    row = await get_identity(session, provider, subject)
    if row is None:
        row = OAuthIdentityRow(user_id=user_id, provider=provider, provider_subject=subject, email=normalize_email(email))
        session.add(row)
    await session.flush()
    return row


async def audit(session: AsyncSession, *, event: str, email: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[dict] = None) -> None:
    session.add(AuthAuditRow(event=event, email=normalize_email(email) if email else None, user_id=user_id, event_metadata=metadata or {}))
    await session.flush()
