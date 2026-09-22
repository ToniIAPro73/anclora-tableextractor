from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PdfFileRow


async def get_owned(
    session: AsyncSession, doc_id: str, user_id: str
) -> PdfFileRow | None:
    return await session.scalar(
        select(PdfFileRow).where(
            PdfFileRow.documento_id == doc_id,
            PdfFileRow.user_id == user_id,
            PdfFileRow.is_deleted.is_(False),
        )
    )
