# TableExtract access model

TableExtract uses closed, invitation-only access. Public registration is not enabled.

## Flow

1. An administrator whose normalized email is listed in `AUTH_ADMIN_EMAILS` creates an invitation with `POST /api/auth/invitations`.
2. The API stores only a SHA-256 token digest. The returned raw token must be delivered through the approved email channel or secret operational channel; it is never logged.
3. The recipient registers once with `POST /api/auth/register`. The invitation is checked for email match, expiry, revocation and prior acceptance, then atomically marked accepted in the same transaction.
4. Password login creates an HttpOnly session cookie. OAuth login accepts only a verified provider email that belongs to an existing user or an active matching invitation.

## Operational configuration

Set `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` and the callback URL to enable GitHub. Google keeps the existing OIDC settings. `AUTH_ADMIN_EMAILS` is a comma-separated allow-list. Passwords are bcrypt-hashed and are never stored or returned.

The `password_credentials`, `oauth_identities`, `auth_invitations` and `auth_audit_events` tables are created by Alembic migration `0002_auth_access_control`. Audit rows contain event metadata only; tokens and passwords are excluded.

## QA

Use the persistent dedicated account `QA_USER_EMAIL` and synthetic invitation addresses. Do not use personal accounts and do not delete the QA user after testing. Never commit `.env.local` or paste its values into issue comments, test reports or logs.
