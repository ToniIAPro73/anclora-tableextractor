from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserRow


async def get_by_id(session: AsyncSession, user_id: str) -> UserRow | None:
    return await session.scalar(select(UserRow).where(UserRow.user_id == user_id))


async def get_by_email(session: AsyncSession, email: str) -> UserRow | None:
    return await session.scalar(select(UserRow).where(UserRow.email == email))


async def upsert(
    session: AsyncSession,
    *,
    user_id: str,
    email: str,
    name: str = "",
    picture: str | None = None,
    is_test_user: bool = False,
) -> UserRow:
    row = await get_by_email(session, email)
    if row is None:
        row = UserRow(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture,
            is_test_user=is_test_user,
        )
        session.add(row)
    else:
        row.name = name or row.name
        row.picture = picture
    await session.flush()
    return row
