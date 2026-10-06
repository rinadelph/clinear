# Hoja global identity and workspace switching plan

## Agreed product decisions

- A person's access to an organization requires an explicit active membership.
- Credentials are global to an identity, but a session selects exactly one organization and maps back to its existing organization-local user profile.
- Preserve existing user profiles and their IDs because issues, comments, teams, projects, API keys, and other records reference them.
- Migrate each legacy organization-local user to a distinct global identity and membership. Do not merge duplicate emails automatically.
- Login must let the person select an accessible workspace when the email maps to multiple identities; password verification happens against the selected identity. Switching from an authenticated session is allowed only to another active membership of the same identity, and issues a new org-bound session.

## Choreography / dependency order

1. **Schema and migration audit**: inspect revision-5 migration patterns and all user/credential/session foreign keys. Define new `identity`, `organization_membership`, and identity-keyed credential structures without breaking current tenant-local profile references.
2. **Migration 6**: add identity/membership tables; copy each legacy user to a unique identity and membership; migrate password hashes without rehashing or merging; keep legacy API-key/session ownership valid. Test fresh databases, populated revision-5 databases, repeat/startup safety, duplicate emails, and SQLite/Postgres-compatible DDL.
3. **Auth/store contracts**: list workspaces available to an email without disclosing membership unnecessarily; authenticate only after explicit workspace choice when ambiguous; resolve a session as identity + selected org-local user + org; implement switch that validates an active membership and revokes/replaces the prior org-bound session atomically or safely.
4. **GraphQL/API and authorization**: expose `myWorkspaces` based on authenticated identity and `switchWorkspace` only for browser sessions. Keep API-key requests fixed to their token organization. Reject arbitrary org IDs, inactive memberships, suspended users, and cross-identity switching. Preserve admin membership management semantics.
5. **UI wiring**: login workspace selection for duplicate-email identities; workspace selector only lists the current identity's authorized memberships; switching updates the cookie, browser URL/app state, and reloads organization-scoped data together. On failure keep the old workspace intact. Clearly distinguish switching from adding/inviting.
6. **Verification**: migration tests; duplicate-email login tests; same-identity allowed switch; non-member/cross-identity/inactive rejection; API-key remains org-bound; browser switch changes workspace name and issue/member data, survives refresh/back/forward, and never shows stale cross-org state; run full backend/frontend/Compose checks.

## Breaking points and safeguards

- Duplicate emails are deliberately not merged. A password from one legacy profile must not grant access to another identity that happens to share that email.
- Legacy `password_credential.user_id` values point to org-local profiles. Migration must preserve each hash exactly while mapping to its own newly created identity.
- API keys, issue relations, team membership, project membership, and existing writer validation continue using org-local user IDs; do not globally rewrite these references in this phase.
- Existing browser sessions remain tied to their original org-local user and org; either preserve them as legacy-selected sessions or invalidate them deliberately with an explicit documented migration behavior. Never infer new cross-org membership from a legacy session alone.
- Identity-to-membership mapping must enforce unique membership per identity/org and retain organization isolation in every GraphQL resolver/store query.
- Workspace-switch failures must not clear or partially replace the existing session or UI data.
- Agent execution and server-shared saved Views are separate missing capabilities; do not fabricate either while implementing identity switching.

## Acceptance evidence targets

- `tests/test_server_backend.py`: migration from revision 5 preserves users and hashes, duplicate-email identities remain separate, user listing is membership scoped, switching access-control matrix passes.
- Frontend build and `git diff --check` pass; Compose/migration checks pass.
- `agent-browser` against a rebuilt local app: select among duplicate-email workspaces; switch to an authorized workspace; verify URL/name/data; refresh and back/forward; attempt unauthorized switch and verify current workspace/data remain unchanged.
