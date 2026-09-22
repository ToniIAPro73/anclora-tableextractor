from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserSessionRow


async def get_valid(session: AsyncSession, token: str) -> UserSessionRow | None:
    row = await session.scalar(
        select(UserSessionRow).where(UserSessionRow.session_token == token)
    )
    if row and row.expires_at <= datetime.now(timezone.utc):
        return None
    return row


async def upsert(
    session: AsyncSession, *, token: str, user_id: str, expires_at: datetime
) -> UserSessionRow:
    row = await session.get(UserSessionRow, token)
    if row is None:
        row = UserSessionRow(
            session_token=token, user_id=user_id, expires_at=expires_at
        )
        session.add(row)
    else:
        row.user_id = user_id
        row.expires_at = expires_at
    await session.flush()
    return row


async def delete_token(session: AsyncSession, token: str) -> None:
    await session.execute(
        delete(UserSessionRow).where(UserSessionRow.session_token == token)
    )
