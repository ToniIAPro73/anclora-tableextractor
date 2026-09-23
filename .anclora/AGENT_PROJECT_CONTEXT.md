# Anclora TableExtract — Agent Project Context

AGENT_PROJECT_CONTEXT_VERSION=1.0
STATUS=ACTIVE

## Project identity

APPLICATION_NAME=Anclora TableExtract
REPOSITORY=anclora-tableextractor
PROJECT_ROLE=Application (PDF table extraction, review and export)
PRODUCT_FAMILY=Anclora Group

## Authority and bootstrap

This repository follows the workspace policy in `../ANCLORA_WORKSPACE_AGENT_POLICY.md`.
The current explicit instruction from Toni has operational precedence, followed by
the workspace policy, these contracts, repository instructions and generic defaults.

Before changing code, agents must read, in order:

1. Current instruction from Toni.
2. Workspace policy.
3. Repository instructions, when present.
4. This file.
5. `.anclora/PRODUCTION_RUNTIME.md`.
6. `.anclora/AOS_ADOPTION.md`.
7. Task-specific documentation and tests.

## Task routing

| Domain | Primary authority |
| --- | --- |
| Runtime, environment and database | `.anclora/PRODUCTION_RUNTIME.md` |
| Governance and agent behavior | `.anclora/AOS_ADOPTION.md` |
| Product behavior | `README.md`, `memory/PRD.md`, existing API/frontend contracts |
| API and persistence | `backend/server.py`, `backend/models.py`, `backend/db/` |
| QA and data isolation | `.anclora/PRODUCTION_RUNTIME.md`, `backend/tests/`, `backend/scripts/` |

## Non-negotiable invariants

- Local runtime is deliberately production-backed through Neon; do not create a substitute database.
- PostgreSQL access is through SQLAlchemy 2.x and Alembic. MongoDB is not a runtime dependency.
- All user-owned reads, updates, deletes and exports are scoped by `user_id`.
- QA uses only the dedicated `QA_USER_EMAIL`; never use a personal or real customer account.
- Secrets and `.env*` files are never committed or printed.
- Destructive scripts default to dry-run and are restricted to the QA user.
- Database migrations against production require `ALLOW_PRODUCTION_MIGRATIONS=true`.
- Preserve existing API paths, JSON field names and prefixed string IDs where possible.

## Git and delivery

**WORKING_BRANCH=development**
**FEATURE_BRANCHES=DISALLOWED**

All development work must be performed directly on the `development` branch.

- Do NOT create feature branches (`feat/*`, `fix/*`, `refactor/*`, `reconcile/*`).
- Commit and push validated work directly to `development`.
- Promotion follows the canonical flow: `development` → `staging` → `production` → `main`.
- Use `.github/workflows/promote.yml` for promotion (fast-forward only).
- Never force-push to any canonical branch.
- Never commit functional changes directly to `staging`, `production`, or `main`.
