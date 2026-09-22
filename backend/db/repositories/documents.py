from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import DocumentRow, ExtractedTableRow, PdfFileRow


async def get(session: AsyncSession, doc_id: str, user_id: str) -> DocumentRow | None:
    return await session.scalar(
        select(DocumentRow).where(
            DocumentRow.id == doc_id, DocumentRow.user_id == user_id
        )
    )


async def list_for_user(session: AsyncSession, user_id: str) -> list[DocumentRow]:
    result = await session.scalars(
        select(DocumentRow)
        .where(DocumentRow.user_id == user_id)
        .order_by(DocumentRow.fecha_carga.desc())
        .limit(500)
    )
    return list(result)


async def tables_for_user(
    session: AsyncSession, doc_id: str, user_id: str
) -> list[ExtractedTableRow]:
    result = await session.scalars(
        select(ExtractedTableRow)
        .where(
            ExtractedTableRow.documento_id == doc_id,
            ExtractedTableRow.user_id == user_id,
        )
        .limit(200)
    )
    return list(result)


async def delete_owned(session: AsyncSession, doc_id: str, user_id: str) -> bool:
    result = await session.execute(
        delete(DocumentRow).where(
            DocumentRow.id == doc_id, DocumentRow.user_id == user_id
        )
    )
    return result.rowcount == 1


async def delete_tables_owned(session: AsyncSession, doc_id: str, user_id: str) -> None:
    await session.execute(
        delete(ExtractedTableRow).where(
            ExtractedTableRow.documento_id == doc_id,
            ExtractedTableRow.user_id == user_id,
        )
    )


async def delete_pdf_owned(session: AsyncSession, doc_id: str, user_id: str) -> None:
    await session.execute(
        delete(PdfFileRow).where(
            PdfFileRow.documento_id == doc_id, PdfFileRow.user_id == user_id
        )
    )
