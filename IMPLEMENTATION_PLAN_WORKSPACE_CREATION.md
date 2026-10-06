# Workspace and team-flow repair plan

## Choreography and dependencies

1. **Diagnose team creation first.** Capture the actual GraphQL response/body for `teamCreate` and the frontend's state after submitting. Existing browser evidence shows an HTTP 200, which does not prove GraphQL success. This diagnosis determines whether the server mutation needs repair or the form needs clearer response/error handling.
2. **Implement authenticated workspace creation.** Add `workspaceCreate` to the GraphQL schema and resolver; add a transactional writer/store operation that validates a normalized unique URL key, verifies current-user authentication, creates the organization, global identity membership, workspace profile, and returns the workspace. Add a create-workspace form/action reachable from the workspace picker. This depends on confirming table constraints and store conventions.
3. **Repair workspace-selected login.** Ensure email login and API-key login honor the selected workspace only when the authenticated identity is an active member. Existing change in `app.py` handles only API-key mode; verify and correct both modes without widening access.
4. **Build and run frontend/server locally** against the already isolated SQLite E2E DB, preserving existing user databases and unrelated processes.
5. **Browser E2E verification:** create a new workspace as the logged-in user; confirm it appears in the picker and survives reload; switch both directions between workspaces; create a team and confirm visible result and DB persistence; add a local member and confirm refreshed UI/persistence. Observe failed requests and console errors. No real email or external services.

## Breaking points / guardrails

- Multi-tenant isolation: every new organization/profile/membership row must be linked consistently; no user must gain access to another workspace by ID guessing.
- URL keys are globally unique. Normalize once and report conflicts without partial writes.
- Browser sessions require a profile for the target workspace. Create that profile/membership in one transaction and preserve creator admin privilege.
- GraphQL can return HTTP 200 with `errors`; inspect response body, not status alone.
- Browser controls are event-driven; confirm input values, enabled state, and result before assuming submit succeeded.
- Keep existing dirty files intact; inspect diffs and do not stage or reset unrelated changes.
- Testing contract: no unit tests. Use E2E browser user flows and build/compile checks only.

## Expected behavior

- Workspace create: admin submits name/key; duplicate/invalid key gives visible error; success appears as active workspace and persists after reload.
- Team create: admin submit either adds team and confirmation or visible GraphQL error; team appears in sidebar and persisted DB.
- Login/switch: selected workspace maps to an active membership; unsupported membership is rejected; active selection persists through reload.
- Member add: local user row appears without email delivery.
