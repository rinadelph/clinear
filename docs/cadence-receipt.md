# Cadence mutation lost-response receipt

## Contract

`frontend/src/main.tsx` TeamCycleSettings near line 236 requires a weekday, guards busy/loading/error/missing saved state, posts `teamCycleCadenceEnable(teamId,weekday)`, and applies authoritative response only on success. After navigation/remount, `teamCycleCadence(teamId)` reads persisted state, so a lost mutation response must be reconciled by read rather than blind repeated submit. `cliniar_server/resolvers.py#L339-L347` enforces admin and org, `writer.py#L154-L187` commits team settings plus Current/two Upcoming atomically; `db.py` uniqueness on team+number and team+boundary ensures one schedule slot per interval. The invariant is exactly one accepted enablement resulting in three unique cycle rows, stable Current ID and saved weekday, even when the browser does not receive the mutation response.

## Isolation

Fresh `/tmp/hoja-cadence-receipt/receipt.db` rev12 with one authorized fixture team RCT disabled and zero cycles, service `localhost:8810`, separate `agent-browser` session `cadence-receipt`. Logged in using a private local API key read only inside a subprocess without echo. No `--open`; original DB, all `hoja-live` tabs t1/t2/t4–t9, and external Linear remain untouched. A page-local fetch wrapper will forward only the `mutation EnableCadence(` request to this isolated backend, wait for its completed response (commit), then hold or reject the response to the page; all other traffic passes normally. The backend DB must independently show three rows **before** the browser response is withheld—otherwise a timeout is not commit proof.

## Exercise

In isolated `cadence-receipt`, a page-local `window.fetch` wrapper forwarded exactly the `mutation EnableCadence(` POST to the real `localhost:8810/graphql` backend, waited for its HTTP200 response, and held the response Promise from the page. The button visibly remained **Enabling…**, with one captured mutation request. **Before releasing the response**, a new SQLite connection read `cadence_enabled=true`, weekday Monday (0), active pointer set, and three rows numbered 1/2/3 with unique boundary keys: commit independently proven, not inferred from timeout. Navigated to team Cycles while the browser response was still held, then rejected that one browser Promise with a fixture lost-response error. Cycles showed rows 1/2/3; no second mutation was submitted. This reproduces a real backend commit with a lost browser receipt.


## Verification

Returning to `/workspace/team/rct/cycles/settings` showed saved **Monday**, Current Cycle 1 and Upcoming Cycle 2/3 with no enable form or error; a full reload preserved those values. A fresh SQLite connection independently counted exactly three cycle rows, distinct `(team,boundary)` values, enabled weekday 0 and active pointer equal to Cycle 1 ID. Thus receipt reconciliation through the authoritative read prevented accidental retry and duplicate creation. Browser errors and console had no unexpected errors after navigation; sampled isolated GraphQL requests returned 200. The wrapper was restored/removed on navigation/reload. A true backend failure after dispatch, concurrent browser submissions and PostgreSQL commit acknowledgement remain unverified.


## Result

The committed-but-lost-browser-response case was exercised against an isolated **real** backend: authoritative reload showed the one intended cadence exactly once. No stale-state product defect or code repair was demonstrated; only this audit document was added, with no version bump. The original Hoja database, dirty work, existing headed tabs/services and Linear remained untouched; `git diff --check` passed, no unit tests/commit/release. Remaining gaps are real server failure after dispatch, multi-tab races and PostgreSQL concurrency; this result must not be generalized to those cases.

