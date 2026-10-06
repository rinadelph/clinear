# Cadence settings stale-response investigation

## Contract

`frontend/src/main.tsx` TeamCycleSettings around line 236 receives a team selected by App route, queries `teamCycleCadence(teamId)`, and writes saved/weekday/loading/error state. Current implementation increments `readGeneration` on a read and cleanup, gates callbacks by both `live` and generation; a Retry changes `readAttempt` to run a new query. The originating team ID is closed over by the effect, and route changes may unmount or reuse this component. The user-visible invariant is that Beta settings must never render Alpha's response, even if Alpha's request resolves later. For a controlled A→B request and B→A completion, use an isolated browser-only interception on the cadence GraphQL query: hold A, navigate to B, return B then release A; inspect heading, weekday, saved status, loading/error and request log. If an interception cannot delay **only** the cadence query while allowing App startup and navigation, this race cannot be claimed reproduced.

## Safety

Use only separate agent-browser session `cadence-retry` against local disposable `localhost:8807` and `/tmp/hoja-cadence-read-retry/retry.db`; no external Linear or original Hoja endpoint is intercepted. Existing `hoja-live` tabs t1/t2/t4–t9 and services stay open. The isolated fixture currently has one team; a second distinguishable fixture team must be added there (not in original DB) before an A/B test. This is a read-only browser probe: do not submit the cadence enable mutation. Current worktree is substantially dirty; do not overwrite unrelated edits. No unit tests.

## Reproduction

In separate `cadence-retry` browser session on isolated `localhost:8807`, a second fixture team Retry Beta was added only to the `/tmp` DB. A page-local `window.fetch` wrapper intercepted **only** requests whose POST body contained `query Cadence(`; all other requests passed through to the isolated server, and no mutation was intercepted or submitted. It held Alpha request A, navigated to Beta via team sidebar/Cycles/settings to start B, released mocked Beta B (enabled Friday, America/New_York), then released mocked Alpha A (enabled Tuesday, UTC). Visible Beta heading/status remained Beta Friday before and after late A; no browser errors/console failure. Repeated in reverse: held Beta A, navigated Alpha B, delivered Alpha disabled then late Beta enabled; visible Alpha heading/form stayed Alpha disabled. The fixture values were clearly synthetic browser-only responses, never written to SQLite. Network request log recorded normal isolated GraphQL traffic; held cadence requests were observed in wrapper state by team ID. Both A/B orders were browser-visible and produced **no stale-state bug**.


## Repair

Pending demonstrated result.

## Verification

The first A→B/B→A ordering held Alpha then Beta and left Beta Friday visible; the second held Beta then Alpha and left Alpha's blank weekday form visible. After each synthetic delivery, the selected URL/heading agreed with visible settings and no other team's status appeared. Interception was restored in the isolated browser; session errors/console had no new errors. No form submission or DB write occurred. The existing authenticated real-data settings read and Retry behavior were verified separately in `docs/cadence-settings-hardening.md#Verification`. Build was not needed because no product source changed; `git diff --check` passed.


## Result

Controlled out-of-order **read** responses were reproduced in both directions in an isolated browser; the current TeamCycleSettings guard prevented stale UI state. No repair or version bump was warranted. The experiment does not cover a pending cadence-enable mutation response, forced auth expiry, multi-workspace switching within one mounted component, or every browser/network race. Existing dirty files, original Hoja DB, Linear and `hoja-live` tabs were untouched; only a disposable fixture team, browser-only mocks and this audit document were added. No unit tests, commit or release.

