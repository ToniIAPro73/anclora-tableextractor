# Canonical user review and release protocol — workspace policy v2.2
DEVELOPMENT_VALIDATION_REQUIRED=true
CHANGES_REMAIN_UNCOMMITTED_UNTIL_VALIDATED=true
COMMIT_PUSH_REQUIRES_EXPLICIT_USER_VALIDATION=true
AUTO_COMMIT_AFTER_VALIDATION=false
AUTO_PUSH_DEVELOPMENT=false
AUTO_PUSH_WORK_BRANCH=false
PREVIEW_VALIDATION_REQUIRED_BEFORE_PROMOTION=true
PROMOTION_AUTHORIZATION_TOKEN=PROMOTE=FULL
PROMOTION_DISPATCH_FULL_CHAIN_ONCE=true
PROMOTION_REQUIRES_PREVIEW_REVIEWED_SHA=true
PROMOTION_AGENT_WAITS_FOR_SOURCE_CI=false
PROMOTION_WAIT_FOR_WORKFLOW_COMPLETION=false
PROMOTION_AGENT_POLLS_CI_OR_DEPLOYMENT=false
PROMOTION_AGENT_PER_HOP_VERIFICATION=false
PROMOTION_USER_VERIFIES_EACH_BRANCH=true
PROMOTION_DISPATCH_IMMEDIATELY=true
PROMOTION_FORCE_PUSH_ALLOWED=false
PROMOTION_PROTOCOL=Local changes -> explicit Toni validation in development -> commit/push development -> Toni Preview review -> PROMOTE=FULL + exact reviewed SHA -> one asynchronous full-chain workflow

Toni validates every change in the development environment before the agent commits or pushes it. After the push, the agent waits for Toni to review Preview. Only Toni's exact PROMOTE=FULL token authorizes the complete ordered staging -> production -> main chain, using the exact SHA reviewed in Preview. The agent dispatches one full-chain workflow per repository, does not wait for or poll CI/deployment/workflow completion, and does not verify individual target branches. That workflow rejects failed source status and branch divergence, permits pending checks, validates all target branches before writing, and updates all three refs sequentially with fast-forward pushes, and stops if development moved after Preview review. Toni reviews the resulting environments.

# Anclora TableExtract — Production Runtime Contract

PRODUCTION_RUNTIME_MANIFEST_VERSION=2.0
PROMOTION_REPORT=SINGLE_SUMMARY_AT_END
PROMOTION_PARALLEL_ACROSS_REPOS=true
PROMOTION_MULTI_REPO_SCOPE_ALLOWED=true
PROMOTION_STOP_ON_GATE_FAILURE=true
PROMOTION_REQUIRES_PRE_STEP_GATES=true
PROMOTION_MECHANISM=.github/workflows/promote.yml
PROMOTION_FLOW=development->staging->production->main
PROMOTION_SUPPORTED=true
SECRET_COMMIT_FORBIDDEN=true
SECRET_OUTPUT_FORBIDDEN=true
PROMOTION_AUTHORIZATION_CLEAR_ON_UNAUTHORIZED_PROMPT=true
PROMOTION_AUTHORIZATION_CLEAR_ON_NEW_SESSION=true
PROMOTION_AUTHORIZATION_SCOPE=CURRENT_TASK_OR_CONVERSATION
AUTO_PROMOTE=false
TEST_EXECUTION_POLICY=BATCHED
STOP_WHEN_SUFFICIENT_EVIDENCE=true
CAVEMAN_GRANULARITY=TASK
CAVEMAN_MODE_DEFAULT=AUTO
TOKEN_ECONOMY_POLICY=ADAPTIVE
QA_MODE_DEFAULT=AUTO
STOP_AFTER_DEVELOPMENT_PUSH=true
PUSH_TARGET=origin/development
FEATURE_BRANCHES=DISALLOWED
DEFAULT_BRANCH=development
WORKING_BRANCH=development
ANCLORA_FLOW_CONTRACT_VERSION=2.0
ANCLORA_FLOW_VERSION=1
STATUS=PRODUCTION_BACKED

## Deployment infrastructure

VERCEL_PROJECT_NAME=anclora-tableextractor
VERCEL_PROJECT_ID=prj_0flR1QDL4GexJRj4mKh1vnportnn
VERCEL_ROOT_DIRECTORY=frontend
VERCEL_FRAMEWORK=create-react-app
VERCEL_PRODUCTION_BRANCH=main
GITHUB_DEFAULT_BRANCH=development
PRODUCTION_DOMAIN=tableextractor.anclora.com
DNS_PROVIDER=Hostinger
DNS_STATUS=CONFIGURED_TLS_PENDING
BACKEND_RUNTIME_EXTERNAL_REQUIRED=true
BACKEND_RUNTIME_PROVIDER=Contabo VPS
BACKEND_RUNTIME_CONTAINERIZED=true
BACKEND_REVERSE_PROXY=Caddy
BACKEND_DEPLOY_SOURCE=main
BACKEND_DEPLOY_MODEL=Docker image pinned by SHA
BACKEND_PRODUCTION_URL=https://api.tableextractor.anclora.com
NEON_RESOURCE_NAME=anclora-tableextractor-db
NEON_RESOURCE_ID=store_l5OIbT2XGoQuziLV
DATABASE_PROVIDER=Neon PostgreSQL
DATABASE_RUNTIME_SCOPE=production
LOCAL_RUNTIME_MODEL=PRODUCTION_BACKED

The Vercel project is frontend-only (`frontend/`). The FastAPI backend remains an
external runtime and must be exposed through `REACT_APP_BACKEND_URL` before a
production deployment is considered functional. The Neon resource is connected
to Vercel Production, Preview and Development; local development uses the same
Production database by contract. DNS remains authoritative at Hostinger.

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

QA_POLICY=WORKSPACE_PROPORTIONAL
FAST_TARGETED_TESTING_POLICY=MINIMUM_SUFFICIENT_SET
FAST_FULL_TEST_SUITE_ALLOWED=false
FULL_GATES_AFTER_EVERY_EDIT=false
REPEAT_UNCHANGED_SUCCESSFUL_GATES=false
VISUAL_QA_EXECUTION=BY_QA_MODE

QA_MINIMUM_FOR_DATABASE_MIGRATION=FULL
QA_MINIMUM_FOR_AUTH=FULL
QA_MINIMUM_FOR_RELEASE_PROMOTION=FULL


AUTH_MODEL=Cookie session-based authentication
SESSION_STORAGE=PostgreSQL user_sessions table
USER_STORAGE=PostgreSQL users table
QA_AUTH_MODEL=DEDICATED_USER
QA_USER_EMAIL=qa.tableextract@anclora.local
QA_DATA_ISOLATION_MODEL=USER_OWNED_RECORDS
QA_WRITE_SCOPE=authenticated QA user records only; never query or mutate another owner's records
QA_DELETE_AFTER_TEST=false
QA_SESSION_HELPER=backend/scripts/create_qa_session.py
QA_SESSION_TTL_MINUTES=15
QA_SESSION_TOKEN_HANDOFF=temporary_mode_0600_file_only

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

EXPLICIT_PROMOTION_ALLOWED=true
PROMOTION_OLD_AUTHORIZATION_PERSISTS=false

All implementation changes are committed and pushed directly to `development` by default.
Promotion branches receive only explicitly requested, gated fast-forward promotions through
the governed workflow.

<!-- ANCLORA-MODS:START -->
ANCLORA_MODS_COMMON_CONTRACT_VERSION=1.0.0
Canonical shared rules: [Anclora Common Agent Contract](../anclora-mods/contracts/ANCLORA_COMMON_AGENT_CONTRACT_V1.md) and [Flow Amendment v2](../anclora-mods/ANCLORA_FLUJO_UNICO_V2.md). Repository-specific facts remain in this repository's `.anclora/` contracts.
<!-- ANCLORA-MODS:END -->
