from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import OAuthStateRow


async def get(session: AsyncSession, state: str) -> OAuthStateRow | None:
    return await session.get(OAuthStateRow, state)
