"""Google Sheets export via user OAuth2 (spreadsheets scope).

Used ONLY to write validated tables into a new spreadsheet the user owns.
"""

import logging
import warnings
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
GOOGLE_CLIENT_ID = _settings.google_client_id
GOOGLE_CLIENT_SECRET = _settings.google_client_secret
REDIRECT_URI = _settings.google_sheets_redirect_uri
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

_CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


def is_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and REDIRECT_URI)


def build_auth_url(state: str) -> str:
    flow = Flow.from_client_config(
        _CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
        include_granted_scopes="true",
    )
    return url


def exchange_code(code: str) -> dict:
    flow = Flow.from_client_config(
        _CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
        "expires_at": (
            creds.expiry.replace(tzinfo=timezone.utc).isoformat()
            if creds.expiry
            else (datetime.now(timezone.utc) + timedelta(minutes=55)).isoformat()
        ),
    }


def _creds_from_token(token: dict) -> Credentials:
    creds = Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri=token.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token.get("client_id", GOOGLE_CLIENT_ID),
        client_secret=token.get("client_secret", GOOGLE_CLIENT_SECRET),
        scopes=token.get("scopes", SCOPES),
    )
    exp = token.get("expires_at")
    needs_refresh = True
    if exp:
        dt = datetime.fromisoformat(exp)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        needs_refresh = datetime.now(timezone.utc) >= dt
    if needs_refresh and creds.refresh_token:
        creds.refresh(GoogleRequest())
    return creds


def _grid(table):
    ncols = table["num_columnas"]
    nrows = table["num_filas"]
    values = [["" for _ in range(ncols)] for _ in range(nrows)]
    pages = [[1 for _ in range(ncols)] for _ in range(nrows)]
    for cell in table["cells"]:
        r, c = cell["fila"], cell["columna"]
        if r < nrows and c < ncols:
            values[r][c] = cell.get("valor", "")
            pages[r][c] = cell.get("pagina", 1)
    return table["columnas"], values, pages


def export_document_to_sheets(token: dict, document: dict, tables: list):
    """Create a new spreadsheet and write each table to its own sheet.
    Returns (spreadsheet_url, updated_token_or_None)."""
    creds = _creds_from_token(token)
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    title = f"Anclora · {document['nombre_archivo']}"
    sheets_meta = []
    for ti, t in enumerate(tables or [{}]):
        name = f"Tabla {ti + 1}"
        sheets_meta.append({"properties": {"title": name}})
    if not tables:
        sheets_meta = [{"properties": {"title": "Vacío"}}]

    spreadsheet = (
        service.spreadsheets()
        .create(body={"properties": {"title": title}, "sheets": sheets_meta})
        .execute()
    )
    ss_id = spreadsheet["spreadsheetId"]
    ss_url = spreadsheet.get(
        "spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{ss_id}"
    )

    data = []
    for ti, t in enumerate(tables):
        cols, values, pages = _grid(t)
        header = list(cols) + ["_pagina_origen"]
        rows = [header]
        for r in range(len(values)):
            page_vals = sorted({pages[r][c] for c in range(len(cols))})
            rows.append(
                [values[r][c] for c in range(len(cols))]
                + [", ".join(str(p) for p in page_vals)]
            )
        data.append({"range": f"Tabla {ti + 1}!A1", "values": rows})

    if data:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=ss_id, body={"valueInputOption": "RAW", "data": data}
        ).execute()

    updated = None
    if creds.token != token.get("access_token"):
        updated = {
            **token,
            "access_token": creds.token,
            "expires_at": (
                creds.expiry.replace(tzinfo=timezone.utc).isoformat()
                if creds.expiry
                else token.get("expires_at")
            ),
        }
    return ss_url, updated
