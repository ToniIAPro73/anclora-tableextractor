import asyncio
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from config import get_settings
from db.session import close_engine, get_session_factory
from db.repositories.users import get_by_email, upsert


async def main():
    settings = get_settings()
    async with get_session_factory()() as session:
        row = await get_by_email(session, settings.qa_user_email)
        if row and not row.is_test_user:
            raise RuntimeError("Configured QA user exists but is_test_user is false")
        if row is None:
            await upsert(
                session,
                user_id="user_qa_tableextract",
                email=settings.qa_user_email,
                name="TableExtract QA",
                is_test_user=True,
            )
        await session.commit()
    print("QA user ready")
    await close_engine()


if __name__ == "__main__":
    asyncio.run(main())
