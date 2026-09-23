from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ExtractedTableRow


async def get_owned(
    session: AsyncSession, table_id: str, doc_id: str, user_id: str
) -> ExtractedTableRow | None:
    return await session.scalar(
        select(ExtractedTableRow).where(
            ExtractedTableRow.id == table_id,
            ExtractedTableRow.documento_id == doc_id,
            ExtractedTableRow.user_id == user_id,
        )
    )
