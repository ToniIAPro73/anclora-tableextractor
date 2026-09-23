# TableExtractor production database

Provider: Neon PostgreSQL. Ownership: Alembic (`backend/alembic`). Runtime uses
the pooled URL; migrations use the unpooled URL and require
`DATABASE_TARGET=production` plus `ALLOW_PRODUCTION_MIGRATIONS=true`.

| Table | Purpose | Sensitive fields |
|---|---|---|
| `users` | Application identities | email, password hash |
| `user_sessions` | Server sessions | session token |
| `documents` | Document metadata and lifecycle | filenames, storage references |
| `extracted_tables` | Extracted table metadata/data | extracted content |
| `pdf_files` | PDF persistence adapter | file bytes, paths, names |
| `google_tokens` | OAuth token storage | provider credentials |
| `oauth_states` | OAuth correlation | state and IDs |
| `alembic_version` | Migration state | none |

No destructive downgrade/reset/truncate/global delete is permitted. QA uses
`qa.tableextract@anclora.local`; secrets remain in ignored 0600 env files.
