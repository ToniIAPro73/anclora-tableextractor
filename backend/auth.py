"""Cookie-session authentication backed by PostgreSQL."""

from __future__ import annotations
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.repositories import sessions, users
from db.session import get_db
from models import User

logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/api/auth")
SESSION_DATA_URL = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)
SESSION_DAYS = 7


def _public_user(row) -> User:
    return User(
        user_id=row.user_id,
        email=row.email,
        name=row.name,
        picture=row.picture,
        is_test_user=row.is_test_user,
        created_at=row.created_at.isoformat(),
    )


async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = session_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session_row = await sessions.get_valid(db, token)
    if not session_row:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user_row = await users.get_by_id(db, session_row.user_id)
    if not user_row:
        raise HTTPException(status_code=401, detail="User not found")
    return _public_user(user_row)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
        max_age=SESSION_DAYS * 24 * 60 * 60,
    )


@auth_router.post("/session")
async def process_session(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    async with httpx.AsyncClient() as http:
        remote = await http.get(SESSION_DATA_URL, headers={"X-Session-ID": session_id})
    if remote.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = remote.json()
    existing = await users.get_by_email(db, data["email"])
    row = await users.upsert(
        db,
        user_id=existing.user_id if existing else f"user_{uuid.uuid4().hex[:12]}",
        email=data["email"],
        name=data.get("name", ""),
        picture=data.get("picture"),
    )
    await sessions.upsert(
        db,
        token=data["session_token"],
        user_id=row.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    )
    await db.commit()
    _set_session_cookie(response, data["session_token"])
    return _public_user(row)


@auth_router.post("/logout")
async def logout(
    response: Response,
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    token = session_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    if token:
        await sessions.delete_token(db, token)
        await db.commit()
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@auth_router.get("/me", response_model=User)
async def me(user: User = Depends(get_current_user)):
    return user
