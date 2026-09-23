# AOS Adoption Declaration — Anclora TableExtract

Repository: `anclora-tableextractor`
Status: Adopted for this migration mission
Governance level: GL-1

## Local canonical sources

- Product and behavior: `README.md`, `memory/PRD.md`, existing API and frontend tests.
- Runtime and operations: `.anclora/PRODUCTION_RUNTIME.md`.
- Agent bootstrap and routing: `.anclora/AGENT_PROJECT_CONTEXT.md`.
- CI workflows: `.github/workflows/`.

These sources are subordinate to the workspace policy and the current explicit
instruction from Toni. Historical implementation notes are not active runtime
authority and must not reintroduce non-public vendor infrastructure.

## Decisions for this migration

1. PostgreSQL/Neon is the sole runtime database after migration.
2. Alembic is the schema history authority; no hand-created production schema.
3. Existing prefixed IDs and API JSON contracts remain stable.
4. QA data is persistent, dedicated and user-scoped; QA cleanup is explicit and dry-run by default.
5. Cross-user access must be denied for every document, table, PDF, thumbnail, mutation and export path.

## Runtime independence

Authentication uses direct Google OAuth/OIDC, LLM inference uses an optional
OpenAI-compatible provider, and file persistence defaults to PostgreSQL BYTEA with
an optional S3-compatible adapter. No coding-agent vendor is a runtime, build or
development dependency.

Review this declaration whenever the database provider, authentication model or
production-backed local runtime changes.
