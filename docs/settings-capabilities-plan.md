# Hoja settings implementation roadmap

## Scope agreed

Build remaining settings as genuinely useful self-hosted Hoja capabilities in
verified batches. Do not enable a destination merely because it appears in the
Linear-inspired sidebar. Billing, external OAuth/code-host integrations, email
delivery, and agent execution remain deferred until concrete providers and
security/hosting contracts are chosen.

## Batch 1 — existing capabilities

### Profile
- Let a user update their display name; keep email read-only (identity-managed).
- Persist through authenticated profile API scoped to the current user/workspace;
  validate non-empty bounded name and return the updated profile.
- UI has loading, save, success/error states and rehydrates from `viewer`.

### Notifications
- Add explicit per-event inbox notification preferences (initially enabled by
  default) for the event kinds Hoja actually creates.
- Persist per authenticated user. Inbox query/read/archive behavior must honor
  disabled kinds; do not imply email/push delivery.
- Provide defaults for existing users with no preference row and test unknown
  kinds/invalid values.

### Issues → Labels
- Provide workspace issue-label create/list/update/delete management using the
  existing label table/API, with optional team scope only if existing API
  semantics prove it safe. Do not conflate project labels with issue labels.
- Restrict destructive/admin operations consistently with the selected
  authorization contract; validate name/color and show API failures.

## Subsequent batches (not included in Batch 1)

1. Templates and project defaults: implement persisted template entities and
   creation/use flows before exposing template settings as functional.
2. Documents, customer requests, releases, asks, loops, custom emojis: each
   needs its own data model, owner/workspace access rules, lifecycle, CRUD/UI,
   tests, and migration plan. Deliver one coherent capability at a time.
3. Usage/import-export/security administration: implement measured counters or
   jobs/policies with observable results and recovery before exposing controls.
4. OAuth/code-host/connected accounts, billing, email delivery, agent execution:
   defer pending explicit provider, secret storage, callback, hosting, and
   operational decisions. Never collect credentials in local storage.

## Shared implementation and verification rules

- Continue using server-derived identity and workspace context; client-supplied
  owner IDs are not trusted. Workspace-admin actions must be backend-authorized.
- Every writable control must have a database/API read-after-write path, strict
  input validation, success/failure feedback, and tests for persistence and
  authorization. Browser preferences such as theme/font size already have a
  server-backed user preference contract.
- Keep unavailable destinations visibly unavailable and non-mutating.
- Verify migrations from fresh and previous schema revisions, backend tests,
  frontend build, E2E navigation, persistence after reload/new session, and
  member/admin access boundaries. Preserve current uncommitted work; do not
  commit during this effort.
