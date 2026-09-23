# Auth-Gated App Testing Playbook

Local QA uses the dedicated persistent user configured by `QA_USER_EMAIL`. It does
not create ad-hoc accounts or access production data belonging to other users.

## Prepare the QA user

From `backend/`, after Alembic has been applied:

```bash
python -m scripts.seed_qa_user
```

For a localhost-only session, set `APP_ENV=development`,
`LOCAL_QA_LOGIN_ENABLED=true` and a local `LOCAL_QA_LOGIN_TOKEN` in
`backend/.env.local`, then call:

```bash
curl -i -X POST http://localhost:8000/api/dev/login \
  -H "X-Local-QA-Token: $LOCAL_QA_LOGIN_TOKEN"
```

The response sets the normal HttpOnly `session_token` cookie. The endpoint is
disabled unless all local guards pass and is never available in production.

## Backend API smoke test

```bash
curl -X GET "$URL/api/health"
curl -X GET "$URL/api/auth/me" --cookie cookies.txt
curl -X POST "$URL/api/documents/upload?lang=es" --cookie cookies.txt -F "files=@/tmp/sample_invoice.pdf"
curl -X GET "$URL/api/documents" --cookie cookies.txt
```

## Cleanup

Cleanup is restricted to the configured QA user and is dry-run by default:

```bash
python -m scripts.cleanup_qa_data
python -m scripts.cleanup_qa_data --execute
```

Never print or commit session tokens, cookies, OAuth credentials, database URLs or
PDF contents.
