"""Create or revoke a short-lived production QA session.

This is an administrative CLI, deliberately not an HTTP endpoint. It only
operates on the configured persistent QA identity and uses the same
``user_sessions`` table and cookie token format as normal authentication.
The raw token is written only to a caller-selected mode-0600 temporary file;
it is never printed or logged.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_settings  # noqa: E402
from db.models import UserSessionRow  # noqa: E402
from db.repositories import sessions, users  # noqa: E402
from db.session import close_engine, get_session_factory  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

SESSION_TTL_MINUTES = 15
MAX_SESSION_TTL_MINUTES = 30


def _cookie_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if path.exists() and path.is_dir():
        raise ValueError("cookie file path must be a file")
    return path


def _write_cookie_file(path: Path, token: str, expires_at: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_token": token,
        "expires_at": expires_at.isoformat(),
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _read_cookie_file(path: Path) -> str:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        raise ValueError("cookie file must have mode 0600")
    payload = json.loads(path.read_text(encoding="utf-8"))
    token = payload.get("session_token")
    if not isinstance(token, str) or not token:
        raise ValueError("cookie file does not contain a valid session")
    return token


async def create_session(cookie_file: Path, ttl_minutes: int = SESSION_TTL_MINUTES) -> None:
    settings = get_settings()
    if ttl_minutes < 1 or ttl_minutes > MAX_SESSION_TTL_MINUTES:
        raise ValueError(f"ttl must be between 1 and {MAX_SESSION_TTL_MINUTES} minutes")

    email = settings.qa_user_email.strip().casefold()
    if email != "qa.tableextract@anclora.local":
        raise RuntimeError("configured QA identity is not the canonical TableExtractor QA user")

    factory = get_session_factory()
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    async with factory() as db:
        row = await users.get_by_email(db, email)
        if row is None:
            raise RuntimeError("canonical TableExtractor QA user does not exist")
        if row.status != "active":
            raise RuntimeError("canonical TableExtractor QA user is not active")
        if row.is_test_user is not True:
            raise RuntimeError("canonical TableExtractor QA user is not marked as a test user")

        await db.execute(delete(UserSessionRow).where(UserSessionRow.user_id == row.user_id))
        await sessions.upsert(db, token=token, user_id=row.user_id, expires_at=expires_at)
        await db.commit()

    try:
        _write_cookie_file(cookie_file, token, expires_at)
    except Exception:
        # Do not leave a live QA session if the temporary handoff failed.
        async with factory() as db:
            await sessions.delete_token(db, token)
            await db.commit()
        raise


async def cleanup_session(cookie_file: Path) -> None:
    token = _read_cookie_file(cookie_file)
    factory = get_session_factory()
    async with factory() as db:
        await sessions.delete_token(db, token)
        await db.commit()
    cookie_file.unlink()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the canonical TableExtractor QA session")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create")
    create.add_argument("--cookie-file", required=True)
    create.add_argument("--ttl-minutes", type=int, default=SESSION_TTL_MINUTES)

    cleanup = subparsers.add_parser("cleanup")
    cleanup.add_argument("--cookie-file", required=True)

    args = parser.parse_args()
    cookie_file = _cookie_path(args.cookie_file)
    try:
        if args.command == "create":
            await create_session(cookie_file, args.ttl_minutes)
            print("QA session: PASS")
            print("cookie file: created with mode 0600")
            print("raw token exposed: NO")
        else:
            await cleanup_session(cookie_file)
            print("QA session cleanup: PASS")
            print("raw token exposed: NO")
        return 0
    finally:
        await close_engine()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
