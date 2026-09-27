# TableExtractor QA access

- QA identity: `qa.tableextract@anclora.local`
- Frontend: `https://tableextractor.anclora.com`
- Backend: `https://api.tableextractor.anclora.com`
- Auth mechanism: PostgreSQL-backed HttpOnly cookie sessions
- Persistent user requirement: `is_test_user=true`, active status
- Secret source: no password is required for the governed production helper

## Smoke procedure

Run `backend/scripts/create_qa_session.py create` with a mode-0600 temporary
cookie file, call the authenticated `/api/auth/me` endpoint, perform browser QA
with that normal session, then run the same CLI with `cleanup`. The helper uses
the normal `user_sessions` table, enforces a short TTL, replaces prior sessions
for this QA identity, and never prints the raw token.

Do not add password authentication, use local QA bypass settings in production,
use Toni's account, use admin accounts, or test with real documents/data.
