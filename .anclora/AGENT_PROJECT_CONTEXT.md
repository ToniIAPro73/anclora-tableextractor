# Anclora TableExtract — Agent Project Context

AGENT_PROJECT_CONTEXT_VERSION=2.0
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

## Canonical QA & Adaptive Execution Bootstrap

Workspace governance defines:
[`../../ANCLORA_WORKSPACE_AGENT_POLICY.md`](../../ANCLORA_WORKSPACE_AGENT_POLICY.md)

Defaults:
- `QA_MODE=AUTO`
- `CAVEMAN_MODE=AUTO`
- `TOKEN_ECONOMY_POLICY=ADAPTIVE`

QA classification determines verification depth:
- `FAST`: minimum sufficient targeted validation; full repository test suites prohibited by default; stops when sufficient evidence exists.
- `STANDARD`: focused functional verification; stops when sufficient evidence exists.
- `FULL`: comprehensive verification; batched at meaningful boundaries.

Caveman classification determines reasoning/exploration economy:
- Dynamically evaluated at task / phase / coherent cluster granularity.
- Deterministic, repetitive, low-ambiguity tasks -> `CAVEMAN=ON`.
- Architectural design, investigation, diagnosis, ambiguity, security, DB design -> `CAVEMAN=OFF`.
- Unexpected failure or ambiguity -> immediate switch `ON -> OFF` before diagnosis.

Task-level historical boilerplate does not override workspace classifications.
Only explicit mission tokens change modes:
- `QA_OVERRIDE=FAST|STANDARD|FULL`
- `CAVEMAN_OVERRIDE=ON|OFF`

Testing, lint, and build execution must follow the workspace batched execution cadence:
no repeated gates per micro-edit, and no rerun of unchanged successful gates without invalidation.
Repository-specific runtime minima are defined in [`PRODUCTION_RUNTIME.md`](PRODUCTION_RUNTIME.md).

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
**DEFAULT_BRANCH=development**
**FEATURE_BRANCHES=DISALLOWED**

All development work must be performed directly on the `development` branch.

- Do NOT create feature branches (`feat/*`, `fix/*`, `refactor/*`, `reconcile/*`).
- Commit and push validated work directly to `development`.
- Promotion follows the canonical flow: `development` → `staging` → `production` → `main`.
- Use `.github/workflows/promote.yml` for promotion (fast-forward only).
- Never force-push to any canonical branch.
- Never commit functional changes directly to `staging`, `production`, or `main`.

Runtime independence: authentication is direct Google OAuth/OIDC, LLM inference
uses an optional public OpenAI-compatible adapter, and PDF persistence defaults to
PostgreSQL BYTEA with optional S3-compatible storage. No coding-agent vendor is
required by runtime, build, CI or development tooling.
