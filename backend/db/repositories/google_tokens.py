from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import GoogleTokenRow


async def get(session: AsyncSession, user_id: str) -> GoogleTokenRow | None:
    return await session.get(GoogleTokenRow, user_id)
