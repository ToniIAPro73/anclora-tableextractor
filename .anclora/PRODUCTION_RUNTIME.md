# Anclora TableExtract — Production Runtime Contract

PRODUCTION_RUNTIME_MANIFEST_VERSION=1.0
STATUS=PRODUCTION_BACKED

## Runtime topology

```text
React frontend -> FastAPI backend -> SQLAlchemy 2.x -> Neon PostgreSQL
                                  -> PostgreSQL BYTEA or optional S3-compatible storage
                                  -> Google OAuth / Google Sheets (optional)
```

`LOCAL_RUNTIME_MODEL=PRODUCTION_BACKED`: local backend execution intentionally uses
the same Neon production database as production. Do not create a local, SQLite,
preview or development database unless Toni explicitly changes this contract.

## Database and migrations

DATABASE_PROVIDER=Neon PostgreSQL
DATABASE_RUNTIME_SCOPE=production
DATABASE_TARGET=production
ORM=SQLAlchemy 2.x async
DRIVER=psycopg 3
MIGRATION_SYSTEM=Alembic
MIGRATION_CONFIRMATION_REQUIRED=false
PRODUCTION_MIGRATIONS_ALLOWED=true

Runtime uses `DATABASE_URL`; Alembic prefers `DATABASE_URL_UNPOOLED` and falls back
to `DATABASE_URL`. If `DATABASE_TARGET=production`, Alembic must refuse to run unless
`ALLOW_PRODUCTION_MIGRATIONS=true` is explicitly present in the process environment.
Never drop or truncate production data as part of this migration.

## Authentication and QA

AUTH_MODEL=Cookie session-based authentication
SESSION_STORAGE=PostgreSQL user_sessions table
USER_STORAGE=PostgreSQL users table
QA_AUTH_MODEL=DEDICATED_USER
QA_USER_EMAIL=qa.tableextract@anclora.local
QA_DELETE_AFTER_TEST=false

The optional local QA login is available only when `APP_ENV=development`,
`LOCAL_QA_LOGIN_ENABLED=true`, the request originates from localhost and the request
contains the configured `X-Local-QA-Token`. It must use the normal session and
`get_current_user()` path; it is never a production bypass.

## Environment contract

Backend local secrets belong in `backend/.env.local` with mode 0600. Frontend local
configuration belongs in `frontend/.env.local`. Both are ignored by Git. Versioned
`.env.example` files contain names and safe placeholders only.

Required/optional names include:

`APP_ENV`, `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `DATABASE_TARGET`,
`ALLOW_PRODUCTION_MIGRATIONS`, `FRONTEND_URL`, `CORS_ORIGINS`, `QA_USER_EMAIL`,
`LOCAL_QA_LOGIN_ENABLED`, `LOCAL_QA_LOGIN_TOKEN`, `GOOGLE_CLIENT_ID`,
`GOOGLE_AUTH_CLIENT_ID`, `GOOGLE_AUTH_CLIENT_SECRET`, `GOOGLE_AUTH_REDIRECT_URI`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_SHEETS_REDIRECT_URI`,
`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`,
`OBJECT_STORAGE_BACKEND`, `OBJECT_STORAGE_ENDPOINT_URL`, `OBJECT_STORAGE_REGION`,
`OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY_ID`,
`OBJECT_STORAGE_SECRET_ACCESS_KEY`, `DATABASE_PDF_MAX_BYTES`,
`REACT_APP_BACKEND_URL`.

Authentication is direct Google OAuth/OIDC with minimal `openid email profile`
scopes. Google Sheets has an independent OAuth flow. LLM inference is optional and
uses a public OpenAI-compatible API adapter. PDF storage defaults to PostgreSQL
BYTEA and may use an explicitly configured S3-compatible backend.

Never print connection strings, passwords, OAuth credentials, cookies, session
tokens, PDF contents or LLM keys.

## Git delivery

WORKING_BRANCH=development
DEFAULT_BRANCH=development
FEATURE_BRANCHES=DISALLOWED
PROMOTION_FLOW=development->staging->production->main

All implementation changes are committed and pushed directly to `development`.
Promotion branches receive only fast-forward promotions through the governed workflow.
