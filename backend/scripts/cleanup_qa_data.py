import argparse
import asyncio
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select

from config import get_settings
from db.models import (
    DocumentRow,
    ExtractedTableRow,
    GoogleTokenRow,
    OAuthStateRow,
    PdfFileRow,
    UserRow,
    UserSessionRow,
)
from db.session import close_engine, get_session_factory


async def main(execute: bool):
    settings = get_settings()
    async with get_session_factory()() as session:
        user = await session.scalar(
            select(UserRow).where(
                UserRow.email == settings.qa_user_email, UserRow.is_test_user.is_(True)
            )
        )
        if not user:
            print(
                "documents: 0\ntables: 0\npdf_files: 0\nsessions: 0\ngoogle_tokens: 0\noauth_states: 0"
            )
            return
        doc_ids = list(
            await session.scalars(
                select(DocumentRow.id).where(DocumentRow.user_id == user.user_id)
            )
        )
        counts = {
            "documents": len(doc_ids),
            "tables": await session.scalar(
                select(func.count())
                .select_from(ExtractedTableRow)
                .where(ExtractedTableRow.user_id == user.user_id)
            ),
            "pdf_files": await session.scalar(
                select(func.count())
                .select_from(PdfFileRow)
                .where(PdfFileRow.user_id == user.user_id)
            ),
            "sessions": await session.scalar(
                select(func.count())
                .select_from(UserSessionRow)
                .where(UserSessionRow.user_id == user.user_id)
            ),
            "google_tokens": await session.scalar(
                select(func.count())
                .select_from(GoogleTokenRow)
                .where(GoogleTokenRow.user_id == user.user_id)
            ),
            "oauth_states": await session.scalar(
                select(func.count())
                .select_from(OAuthStateRow)
                .where(OAuthStateRow.user_id == user.user_id)
            ),
        }
        for key, value in counts.items():
            print(f"{key}: {value}")
        if execute:
            await session.execute(
                delete(OAuthStateRow).where(OAuthStateRow.user_id == user.user_id)
            )
            await session.execute(
                delete(GoogleTokenRow).where(GoogleTokenRow.user_id == user.user_id)
            )
            await session.execute(
                delete(UserSessionRow).where(UserSessionRow.user_id == user.user_id)
            )
            await session.execute(
                delete(PdfFileRow).where(PdfFileRow.user_id == user.user_id)
            )
            await session.execute(
                delete(ExtractedTableRow).where(
                    ExtractedTableRow.user_id == user.user_id
                )
            )
            await session.execute(
                delete(DocumentRow).where(DocumentRow.user_id == user.user_id)
            )
            await session.commit()
            print("QA data cleanup applied")
        else:
            print("dry-run: no data changed")
    await close_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.execute))
