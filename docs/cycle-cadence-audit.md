# Automatic cadence isolated integration audit

## Contract

Approved `docs/team-cycle-cadence-plan.md#Decisions` establishes opt-in team cadence, admin weekday choice, one-week/no-cooldown/two-upcoming, strict local 00:01 half-open UTC intervals, legacy rejection and bounded idempotent read reconciliation; no issue rollover or automatic assignment. Inputs: authenticated organization/team, stored timezone/weekday/anchor and an injectable aware UTC clock. `cliniar_server/writer.py#L154-L200` owns transaction and team locks; `cadence.py#L25-L79,#L89-L180` local conversion and cycle materialization; `db.py#L163-L181,#L373-L397` persist team policy, cycle boundary and unique constraints; `resolvers.py#L325-L353,#L397-L410` mutation/read calls. A successful read is intentionally allowed to materialize due cycles; a repeated read at the same time should not churn identifiers/timestamps or duplicate rows. A failed transaction must leave neither enabled flag nor partial cycles.

## Fixture

All audit writes use new SQLite databases beneath `/tmp/hoja-cadence-audit/`, never `~/.local/share/cliniar/hoja.db`. Each fresh DB is migrated to revision 12 and seeded with explicit unique org/team identifiers; clock values are supplied to Writer, not the server's wall clock. A two-team fixture is used for scoping. No browser tab or Linear page is navigated for these backend checks. Failure injection uses a disposable DB SQLite trigger that raises on the **second** cycle insert, after the enabled flag and first insert in Writer's actual transaction; it is removed before retry. Before/after state is read from fresh DB connections. No unit tests or test files are added/run.

## Rollback

Fresh `/tmp/hoja-cadence-audit/rollback.db` rev12 fixture, one team disabled. A SQLite trigger `BEFORE INSERT ON cycle WHEN NEW.number=2` raised an abort marker. Calling the **real** `Writer.enable_team_cadence` (`writer.py#L154-L187`) had already updated team cadence settings and inserted Cycle 1 within the same `engine.begin()` transaction; insertion of Cycle 2 raised `IntegrityError` before commit. A new connection then read `cadence_enabled=false`, `active_cycle_id=NULL`, **zero** cycle rows. After dropping only the fixture trigger, retry enabled the team with Current 1 and two Upcoming, exactly three rows. No partial approval or duplicate survived failure. This proves SQLite transactional rollback for this injected DB error; PostgreSQL or process termination mid-commit was not exercised.


## DST

Policy in `cliniar_server/cadence.py#L25-L79`: local IANA timezone and weekday, strict **00:01** boundaries; `_local_boundary` round-trips fold candidates and raises `CadenceInputError` when the instant is nonexistent or ambiguous. Reconciler stores UTC instants and advances seven local calendar days (`cadence.py#L120-L140`), not 168 UTC hours. Disposable Writer fixtures (America/New_York) enabling before 2026 spring-forward and fall-back, then reconciling after the next Tuesday, produced first short cycles of **71h** and **73h** respectively (offset transition), subsequent full-week 168h cycles, active 1→2, four total rows and adjacent `[end==next start]` bounds. A UTC Dec31→Jan6 fixture produced first short cycle 120h, then 168h; active 1→2, four rows, adjacent bounds. Direct strict-boundary checks for America/Havana 2026-03-08 00:01 raised nonexistent and 2026-11-01 00:01 raised ambiguous rather than choosing a fold. These last two checks exercised the pure calendar boundary path, not a committed Writer operation; invalid boundary is expected to abort Writer transaction if encountered. Browser rendering across DST was not exercised.


## Teams

The authenticated request context supplies `org_id` and teamId (`resolvers.py#L57-L60,#L333-L348`); Writer locks/selects team by **both** org and ID (`writer.py#L154-L200`), reconciler filters/creates cycles with org/team and unique team+boundary (`cadence.py#L89-L180`). In a disposable two-team SQLite fixture AAA/BBB, enabling AAA at a controlled UTC instant resulted in AAA enabled and three cycle rows, BBB disabled and zero. A fresh read of BBB returned enabled false and did not create rows. A missing team ID raised Team not found. Enabling BBB separately with a different weekday created three BBB rows without changing AAA's weekday or active ID. Persisted counts were three per team, six total, with distinct team IDs; the original database and external Linear were not touched. Cross-**organization** authorization is source scoped but not independently browser-proved in this check.


## Repeated reads

The approved read contract intentionally calls Writer reconciliation from authenticated `teamCycleCadence`, team cycles/activeCycle and team-filtered cycles (`resolvers.py#L325-L350,#L395-L411`); due transitions may materialize rows, but a stable clock should not churn. In `/tmp/hoja-cadence-audit/reads.db`, snapshot before and after two `Writer.reconcile_team_cadence(..., now=fixed)` calls compared every cycle ID/number/created_at/updated_at/completed_at plus team enabled/active pointer/updated_at: **identical**. A new engine/connection returned the same active ID and identical persisted snapshot. Two actual `graphql_sync` teamCycleCadence reads at wall-clock time returned equal data without errors; after the first, the second left persisted fields unchanged (the fixture's current time did not require materialization). No failed read was injected; the separate rollback check proves failure inside the same transactional Writer path before commit, but not a GraphQL read under an injected fault.


## Safety

All new audit DBs and injected trigger live under `/tmp/hoja-cadence-audit/`; original Hoja database was not opened for writes. Before/after repository status remains dirty from prior work; this pass changes only `cliniar_server/cadence.py` plus this new audit document, with version/changelog adjustment required by AGENTS.md because a bugfix was demonstrated. No browser tabs were closed or navigated, and external Linear remained read-only. No unit tests or test files were added/run. Python compilation and `git diff --check` are final checks; PostgreSQL and abrupt process-crash semantics remain unverified.


## Result

Four isolated checks ran: (1) second-insert failure rolled back enablement and all cycles, retry yielded exactly three; (2) New York spring/fall and UTC year boundary persisted ordered adjacent intervals, while Havana 00:01 gap/fold was explicitly rejected by the pure calculator; (3) approving AAA left BBB disabled/zero until independently approved, then each had three scoped rows; (4) stable repeated Writer and GraphQL reads kept IDs, timestamps and pointer unchanged. A **fifth edge check** demonstrated a real defect: after advancing Current from 1 to 3, a backwards clock read demoted the active pointer to 1. The smallest repair in `cliniar_server/cadence.py` rejects a read whose clock precedes the persisted active cycle before any inserts; rerun showed a `CadenceInputError`, unchanged active pointer and unchanged completed-cycle rows. Version/changelog updated as patch 0.21.1. Remaining unknowns include cross-organization browser access, injected failed GraphQL read, a real Havana DST-boundary transaction, PostgreSQL concurrent workers and process crash during commit; no claims of exhaustive correctness.

