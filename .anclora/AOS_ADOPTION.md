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
instruction from Toni. Historical Emergent documentation is not an active runtime
authority and must not reintroduce MongoDB.

## Decisions for this migration

1. PostgreSQL/Neon is the sole runtime database after migration.
2. Alembic is the schema history authority; no hand-created production schema.
3. Existing prefixed IDs and API JSON contracts remain stable.
4. QA data is persistent, dedicated and user-scoped; QA cleanup is explicit and dry-run by default.
5. Cross-user access must be denied for every document, table, PDF, thumbnail, mutation and export path.

## Exceptions and review

The legacy Emergent object storage and OAuth/LLM integrations remain in place unless
needed for the database migration. Their database state must be represented in
PostgreSQL, but this task does not replace external object storage.

Review this declaration whenever the database provider, authentication model or
production-backed local runtime changes.
