# Decision Draft — TableExtract Integration with Anclora Identity

Status: owner decision required. TableExtract is explicitly OUT of Wave 1 of
the Anclora Identity SSO pilot until this decision is made.

## Policy that blocks the integration

`.anclora/AOS_ADOPTION.md` in this repository states, as an adopted governance
position:

> "Authentication uses direct Google OAuth/OIDC ... No coding-agent vendor is
> a runtime, build or development dependency" — declared as a deliberate
> **runtime-independence** decision.

Wave 1's premise (PurgeDoc, CleanSheet, and TableExtract becoming OIDC relying
parties of a shared `anclora-identity` provider) is a direct reversal of that
adopted position for TableExtract specifically: it would introduce a shared,
central identity vendor as a runtime dependency, which is exactly what the
adopted decision rules out. No agent should silently overturn an adopted
governance decision — that is why this app was excluded from Wave 1 rather
than migrated alongside PurgeDoc and CleanSheet.

## Current state (verified in code, 2026-09-27)

TableExtract already has real human authentication, running in parallel
through three separate identity sources feeding one `users` table:

- Google OIDC (`backend/auth.py`: `google_start`/`google_callback`, verifies
  `id_token` issuer/nonce/`email_verified` directly against Google).
- GitHub OAuth (`github_start`/`github_callback`).
- Invitation-gated email/password (bcrypt, `AuthWhitelist`-equivalent via
  `InvitationRow`).

Sessions are opaque, DB-backed tokens (`user_sessions`) in HttpOnly cookies,
not JWTs. Admin role is a flat `AUTH_ADMIN_EMAILS` allowlist. All three
identity sources link into `oauth_identities`/`users` today with no
dependency on any Anclora-operated identity service.

## Impact of migrating

- **If reversed and migrated to Anclora Identity:** TableExtract would gain a
  fourth identity source at anclora-identity, which then needs to reconcile
  against the three that already exist — this is a genuine multi-source
  identity merge (matching by email across Google, GitHub, and local
  password accounts), not a green-field OIDC integration like PurgeDoc/
  CleanSheet. That merge carries real risk of orphaning existing sessions or
  duplicating accounts if done incorrectly.
- **If the policy stands as-is:** TableExtract remains outside the Anclora
  Identity trust boundary indefinitely. Its own users continue to authenticate
  directly against Google/GitHub, with no platform-wide SSO, no shared MFA
  enforcement, and no `platform_roles`/`application_memberships` visibility
  from anclora-identity's perspective.

## Proposed reversal or modification (for owner decision, not pre-decided here)

Two non-exclusive options, presented without a recommendation because this is
explicitly the owner's call, not an engineering default:

1. **Formal reversal**: amend `.anclora/AOS_ADOPTION.md` to retire the
   "runtime independence" clause for identity specifically (it can remain for
   other infrastructure, e.g. coding-agent vendors), then schedule TableExtract
   into a later wave with its own migration plan for reconciling three
   existing identity sources.
2. **Policy stands**: TableExtract stays a Google/GitHub/password app
   permanently, and any future platform-wide identity feature (shared MFA,
   cross-app membership) either doesn't apply to TableExtract or is bridged
   another way (e.g. TableExtract calls `anclora-identity`'s admin API to
   read platform roles without becoming an OIDC relying party itself — not
   evaluated in depth here since it is a materially different integration
   shape).

## Migration sketch (if option 1 is chosen — not started)

1. Add `identity_sub` (nullable, unique) to TableExtract's `users` table,
   mirroring the PurgeDoc/CleanSheet pattern (see
   `anclora-identity/docs/identity/ANCLORA_IDENTITY_WAVE1_CONTRACT.md`).
2. On Anclora Identity login, match by verified email against the existing
   `users` table (populated by any of the three current methods) — never
   auto-create an account, same invariant as PurgeDoc/CleanSheet.
3. Decide whether Google/GitHub direct login stays available in parallel
   indefinitely, is deprecated over a announced window, or is fully replaced
   by routing Google/GitHub through Anclora Identity's own OIDC federation
   (a different, larger change to `anclora-identity` itself, out of scope for
   a TableExtract-side migration).
4. Reconcile `oauth_identities` (TableExtract's own Google/GitHub identity
   table) against the new `identity_sub` — do not delete it; it stays the
   record of the pre-migration identity sources for audit purposes.

## Risks

- Silent account duplication if email matching is case- or
  normalization-sensitive differently than TableExtract's existing lookups.
- Loss of the existing session model's behavior (opaque DB token vs.
  Identity's JWT-cookie-issued-by-app pattern used by PurgeDoc/CleanSheet) —
  TableExtract would need its own bridging logic, not a copy-paste of the
  PurgeDoc/CleanSheet routes.
- Reversing an adopted governance decision sets a precedent other repositories
  with similar "runtime independence" declarations should be checked against
  before any future SSO expansion wave.

## Decision needed

A canonical decision recorded in Governance/Vault (per
`.anclora/AOS_ADOPTION.md`'s own routing to
`anclora-governance/knowledge/MASTER_DECISIONS.md`) on whether to reverse the
runtime-independence clause for identity. Until that decision exists, no code
in this repository should be modified toward Anclora Identity integration.
