# Hoja cadence boundary and legacy audit

## Baseline

All work is read-only source inspection and disposable SQLite fixtures under `/tmp/hoja-cadence-boundary/`; no service or browser tab was navigated. Original `~/.local/share/cliniar/hoja.db`, substantial pre-existing dirty files, and external Linear remained untouched. AGENTS.md and approved `docs/team-cycle-cadence-plan.md#Decisions` were read. No unit tests or test files were added/run.

## Contract

`cliniar_server/cadence.py#L25-L79` converts a team-local IANA timezone/weekday and aware clock to strict 00:01 boundaries; `#L89-L188` reconciles half-open UTC intervals in an existing transaction, bounded to 256 boundary steps, preserving contiguous team cycle numbers and two Upcoming. `writer.py#L154-L200` enables opt-in only for org-scoped teams without unmanaged cycles and uses SQLite `BEGIN IMMEDIATE`/PostgreSQL row lock; disabled reads return no cadence materialization. `db.py#L163-L181,#L373-L397` stores opt-in, anchor, active pointer, cycle timestamps and unique team+number/boundary constraints. `resolvers.py#L325-L351,#L395-L411` triggers reconciliation on authenticated cadence and scoped cycle reads. Approval invariant: no cycle is generated for a disabled legacy team; at chosen weekday 00:00 Current is not prematurely active; at 00:01 Current appears with two upcoming; long downtime catches up in order or fails atomically at its documented bound.

## Fixtures

Three independently migrated revision-12 DBs: `boundary.db` enabled on Tuesday 2026-10-06 00:00 UTC and reconciled 00:01; `downtime.db` enabled 2026-10-01 12:00 UTC (Tuesday weekday) and reconciled 2027-02-01 12:00 UTC; `legacy.db` has a disabled team with a manually inserted Cycle 8 and no cadence boundary. Each uses `Writer` with injected aware clocks and fresh SQLAlchemy connections for persisted-row checks. None points to the original DB.

## Reproduction

Boundary: 00:00 enable returned **no Current**, two Upcoming; at 00:01 Current 1, Upcoming 2/3, exactly three contiguous rows, adjacent `ends_at == next starts_at`, repeated read retained Current ID. Downtime: initial Current 1; after ~123 days Current 18 and Upcoming 19/20, exactly 20 contiguous/adjacent rows, repeated read retained Current ID. Legacy: disabled cadence read yielded enabled false/no upcoming without changing Cycle 8; attempted enable raised a clear legacy-cycle conflict, leaving `cadence_enabled=false` and only Cycle 8. No skipped/duplicate interval defect reproduced for these bounded inputs. A process crash, failure injection during long catch-up, 256+ intervals, or real scheduled worker timing was not exercised.

## Implementation

No code change was justified: all three disposable cases satisfied the approved invariants. Existing `cadence.py` bounded loop and unique constraints prevented duplicate intervals in the observed period, while Writer's disabled gate and legacy conflict left manually seeded Cycle 8 untouched. Repeated same-clock reads kept IDs unchanged. The explicit catch-up cap and transactional rollback are separately documented in `docs/cycle-cadence-audit.md#Rollback`; this turn did not inject a failure during long downtime or exercise the cap, so those states are not newly claimed verified. No cosmetic scheduler changes were made.


## Verification

Fresh-engine reruns on the three `/tmp` fixtures at their injected clocks compared cycle ID/number/start/end/completed rows before and after: **identical** in all cases. Boundary Current1/three adjacent rows; downtime Current18/twenty adjacent rows; legacy disabled/no active/one untouched Cycle8. The original first pass recorded 00:00 no Current/two Upcoming → 00:01 Current1/two Upcoming, and long downtime number sequence 1…20 with end==next-start and stable repeated Current ID. `python3 -m compileall -q cliniar_server` and `git diff --check` passed. A failure injection during long catch-up, a >256-boundary catch-up, process restart under simultaneous workers, and actual browser scheduling at the boundary were not run in this bounded audit. No unit tests were added/run.


## Result

The audited disabled legacy, weekday 00:01 activation, and ~123-day downtime cases behaved according to the approved cadence contract, with no demonstrated bug requiring code changes. Only `docs/hoja-cadence-audit.md` was added during this turn; pre-existing version/code dirty state was not reset or modified for this task. All writes targeted `/tmp/hoja-cadence-boundary/`, not the original database; no `hoja-live` tab was navigated, external Linear stayed read-only. Unverified: failure injection during long catch-up, >256 intervals, cross-process workers, actual real-time boundary and issue rollover (explicitly unsupported). No new version bump because no product code changed, no commit/tag/release.

