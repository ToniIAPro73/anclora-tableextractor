"""Cookie-session authentication backed by PostgreSQL and Google OIDC."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.repositories import sessions, users
from db.session import get_db
from models import User

logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/api/auth")
SESSION_DAYS = 7
STATE_TTL_SECONDS = 600
STATE_COOKIE = "google_oauth_state"
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def _public_user(row) -> User:
    return User(
        user_id=row.user_id,
        email=row.email,
        name=row.name,
        picture=row.picture,
        is_test_user=row.is_test_user,
        created_at=row.created_at.isoformat(),
    )


def _safe_redirect(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/upload"
    return value


def _state_signing_key() -> bytes:
    settings = get_settings()
    secret = settings.google_auth_client_secret or settings.local_qa_login_token
    if not secret:
        raise HTTPException(status_code=503, detail="Google authentication is not configured")
    return secret.encode("utf-8")


def _create_state(redirect: str) -> str:
    payload = {
        "nonce": secrets.token_urlsafe(24),
        "redirect": _safe_redirect(redirect),
        "expires_at": int(time.time()) + STATE_TTL_SECONDS,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=").decode("ascii")
    signature = hmac.new(_state_signing_key(), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _validate_state(state: str | None, cookie_state: str | None) -> str:
    if not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    try:
        encoded, signature = state.split(".", 1)
        expected = hmac.new(
            _state_signing_key(), encoded.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=="))
        if int(payload["expires_at"]) < int(time.time()):
            raise ValueError("expired state")
        return _safe_redirect(payload.get("redirect"))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc


def _google_identity(raw_id_token: str, expected_nonce: str | None = None) -> dict:
    settings = get_settings()
    if not settings.google_auth_client_id:
        raise HTTPException(status_code=503, detail="Google authentication is not configured")
    payload = id_token.verify_oauth2_token(
        raw_id_token, GoogleRequest(), settings.google_auth_client_id
    )
    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise ValueError("unexpected Google issuer")
    if expected_nonce and payload.get("nonce") != expected_nonce:
        raise ValueError("unexpected Google nonce")
    if not payload.get("sub") or not payload.get("email") or not payload.get("email_verified"):
        raise ValueError("Google identity is incomplete or unverified")
    return payload


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


def _clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(STATE_COOKIE, path="/")


@auth_router.get("/google/start")
async def google_start(redirect: str = "/upload"):
    settings = get_settings()
    if not all(
        (settings.google_auth_client_id, settings.google_auth_client_secret, settings.google_auth_redirect_uri)
    ):
        raise HTTPException(status_code=503, detail="Google authentication is not configured")
    state = _create_state(redirect)
    query = urlencode(
        {
            "client_id": settings.google_auth_client_id,
            "redirect_uri": settings.google_auth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(f"{GOOGLE_AUTH_ENDPOINT}?{query}")
    response.set_cookie(
        STATE_COOKIE,
        state,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
        max_age=STATE_TTL_SECONDS,
    )
    return response


@auth_router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    google_oauth_state: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    redirect = _validate_state(state, google_oauth_state)
    if error or not code:
        raise HTTPException(status_code=400, detail="Google authorization was not completed")
    token_payload = {
        "code": code,
        "client_id": settings.google_auth_client_id,
        "client_secret": settings.google_auth_client_secret,
        "redirect_uri": settings.google_auth_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(GOOGLE_TOKEN_ENDPOINT, data=token_payload)
    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Google token exchange failed")
    token_data = token_response.json()
    raw_id_token = token_data.get("id_token")
    if not raw_id_token:
        raise HTTPException(status_code=401, detail="Google identity token missing")
    try:
        identity = _google_identity(raw_id_token, expected_nonce=state)
    except Exception as exc:
        logger.warning("Google identity validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google identity") from exc

    existing = await users.get_by_email(db, identity["email"])
    row = await users.upsert(
        db,
        user_id=existing.user_id if existing else f"google_{identity['sub']}",
        email=identity["email"],
        name=identity.get("name", ""),
        picture=identity.get("picture"),
    )
    session_token = secrets.token_urlsafe(32)
    await sessions.upsert(
        db,
        token=session_token,
        user_id=row.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    )
    await db.commit()
    response = RedirectResponse(f"{settings.frontend_url.rstrip('/')}{redirect}")
    _set_session_cookie(response, session_token)
    _clear_oauth_state_cookie(response)
    return response


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
