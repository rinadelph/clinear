# Cadence enable mutation interception

## Contract

`frontend/src/main.tsx` TeamCycleSettings around line 236 loads saved cadence by team ID. A selected weekday enables `teamCycleCadenceEnable(teamId,weekday)`; on submit `busy` is set and the returned authoritative cadence is applied via `setSaved`. Navigation unmounts the component but the mutation request is not canceled and has no explicit receipt registry. On returning, a fresh `teamCycleCadence` query is the authoritative receipt check. Backend `resolvers.py#L339-L347` enforces admin/org; `writer.py#L154-L187` commits team settings and cycle records transactionally/idempotently. Oracle: a *browser-mocked* success not sent to the backend must not appear persisted after navigation/reload; a mocked failure likewise must leave DB disabled. A true dispatched request with lost response would require querying the server before any retry to avoid duplicate submission.

## Isolation

New disposable SQLite `/tmp/hoja-cadence-interception/interception.db` (rev12, one authorized team, zero cycles), service `localhost:8809`, separate `agent-browser --session cadence-mutation`, API-key login from a private `/tmp` file. Existing headed `hoja-live` t1/t2/t4–t9, original DB, and Linear remain untouched. Interception must match POST body containing `mutation EnableCadence(` and return a synthetic response **without calling original fetch**; all unrelated GraphQL traffic passes only to the isolated service. The DB row count/enable flag will be read independently before/after to prove the mock did not write.

## Delay

Separate `cadence-mutation` browser installed a page-local fetch wrapper that held only POST bodies containing `mutation EnableCadence(`. After selecting Monday and submitting, button visibly said Enabling… and the wrapper recorded exactly one held weekday=0 request. Navigating Back to Cycles unmounted settings; releasing a synthetic success then returning to settings showed a blank, disabled enable form (not synthetic Current). Fresh SQLite read showed `cadence_enabled=false`, **zero** cycle rows. Thus a late response from a browser-only success did **not** make a new mount claim server persistence. It does not model a real server commit whose response is lost; that case must reconcile via an authoritative read, as already verified for ordinary navigation in `docs/team-cycle-cadence.md#Verification`.


## Failure

Repeated with Wednesday: submit showed Enabling… and one held mutation. Navigate Back, release synthetic GraphQL error “fixture mutation failure,” then return to settings. It displayed blank draft/form and no stale error from the old mount. Fresh SQLite still showed disabled false/zero cycles. The failure was browser-mocked, not an actual server rollback; rollback was separately checked in `docs/cycle-cadence-audit.md#Rollback`. No blind second mutation was dispatched.


## Repair

Neither delayed synthetic success nor synthetic error produced stale UI after navigation. TeamCycleSettings is unmounted by route change; its late state updates do not paint the new page, and re-entry queries authoritative persisted state. No product code edit was warranted. A *same-mounted-component team switch while mutation pending* and a real request committed with lost response were not controlled here; do not extrapolate this outcome to those cases.


## Verification

Both scenarios used the isolated authenticated browser at `/workspace/team/ina/cycles/settings` → `/cycles` → settings, with pending button and one held mutation checked before response release. The read-only return query recovered disabled state. Wrapper restore removed interception after each; browser errors and console had no unexpected errors. Independent SQLite inspection confirmed zero cycles and disabled team after both browser-only mock responses. Existing headed tabs were not navigated. `git diff --check` passed; no unit tests added/run.


## Result

Controlled delayed-success and controlled-failure mutation responses across route unmount/re-entry did not create stale visible cadence; no fix/version bump was justified. The mock prevented backend dispatch, so it proves UI behavior only for a non-persisted response. The real committed-but-lost-receipt path, cross-team pending mutation, and auth-expiry remain unverified. Only this audit document was added in the dirty worktree; original DB, Linear and existing tabs/services stayed untouched. No commit/tag/release.

