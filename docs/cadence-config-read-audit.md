# Cadence configuration and read-error audit

## Baseline

This audit uses disposable SQLite data under `/tmp/hoja-cadence-config-audit/` and the already isolated `cadence-retry` browser session/`localhost:8807` only if browser confirmation is needed. Original Hoja `~/.local/share/cliniar/hoja.db`, existing `hoja-live` t1/t2/t4–t9, and Linear remain untouched. Worktree contains extensive prior dirty files (including current cadence changes); AGENTS.md requires a version/changelog bump only if a product code defect is fixed. No unit tests.

## Source map

Configuration path: `cliniar_server/writer.py#L154-L200` validates weekday and team, rejects legacy cycles and reanchor, commits opt-in plus schedule. `cadence.py#L25-L79,#L89-L195` checks timezone/weekday/policy, calculates intervals and materializes cycles. `db.py#L163-L181,#L373-L397` stores opt-in/weekday/anchor/unique cycle boundary. GraphQL `resolvers.py#L325-L351` maps authorized request to Writer. Read path: `frontend/src/main.tsx#L19` `gql()` throws on HTTP or GraphQL errors; TeamCycleSettings `#L236` displays loading/error and genuine manual retry, disables Enable without confirmed settings. Generic `resolvers.py#L61-L69` `_conn` still fixes pageInfo false; `cycles` uses that helper, so a 100-row cycle list is **not** proven exhaustive by its flag. Existing audit docs record successful isolated retry and clock/rollback checks, but this task will reproduce input and read failures independently before editing.

## Cadence

Disposable rev12 `/tmp/hoja-cadence-config-audit/config.db` (one team, injected UTC 2026-10-01 12:00) exercised `Writer.enable_team_cadence`. Weekday -1, 7 and boolean True each raised ValueError; an invalid IANA timezone raised CadenceInputError; a fresh read still had enabled=false/zero cycles. After restoring timezone UTC, Tuesday enable created Current 1 plus Upcoming 2/3. Repeated enable with the same weekday returned the **same active ID**, three rows; reanchor to Wednesday raised ValueError and persisted weekday stayed Tuesday. These valid/missing-invalid/repeat/reload-adjacent checks showed no high-impact configuration parsing or persistence defect requiring a code edit. A stale raw database row with malformed policy fields was not modified or accepted as a valid configuration by source validation; direct browser config input remains a native select. No production defaults were inferred from legacy names.


## Read errors

On the isolated `config.db`, a deliberately unsupported persisted `cadence_policy_version=99` was injected into the fixture team (not through product UI). Two authenticated-context GraphQL `teamCycleCadence(teamId)` calls returned `data:null` with explicit “Unsupported team cycle policy; review settings before retrying.” errors, **not** an empty successful schedule; the three existing cycles remained unchanged. After restoring version 1 in the disposable DB, the same query returned enabled true, weekday Tuesday, one active and two Upcoming, with no error. `frontend/src/main.tsx` `gql()` throws on GraphQL errors and TeamCycleSettings exposes error plus a genuine manual read Retry while disabling Enable; an isolated browser transient network abort/retry was already verified at `docs/cadence-settings-hardening.md#Verification`. The current `r_cycles` connection still uses generic `_conn` with fixed hasNextPage false; no claim of exhaustive >100 cycle pagination is made. A browser presentation of this malformed-policy fixture and auth-expired status was not repeated in this turn. No high-impact read-error swallowing defect reproduced, so no code change.


## Verification

Fresh isolated GraphQL/SQLite checks confirmed the final supported config after restoration was enabled Tuesday with three cycle rows and no errors. The invalid weekday/timezone inputs had produced no writes, valid enable/repeat produced stable IDs, and unsupported policy reads failed explicitly twice before recovery. The separate `cadence-retry` isolated browser still showed no error after its prior successful transient Retry; this turn did not mutate/reload it to fake evidence for the malformed-policy fixture. Python compilation and `git diff --check` passed. No unit tests added/run; browser auth-expiry and >100-cycle list pagination remain unverified.


## Result

No high-impact configuration or cadence-read error defect was reproduced in these isolated fixtures; no product code edit or version bump was justified. Explicit unsupported-policy GraphQL errors were not mistaken for empty success, and restoring valid policy recovered. Only `docs/cadence-config-read-audit.md` was added this turn. All fixture writes targeted `/tmp/hoja-cadence-config-audit/`; original Hoja DB, prior dirty work, headed tabs and external Linear remained untouched. `git diff --check`/compilation passed, no unit tests/commit/release. Generic cycles connection still lacks truthful continuation metadata and is an independently known pagination gap, not fixed by a cadence read retry.

