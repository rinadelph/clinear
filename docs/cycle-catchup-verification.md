# SQLite cycle catch-up cap and rollback

## Contract

`cliniar_server/writer.py#L189-L200` wraps a due team read in one `engine.begin()` transaction and SQLite `BEGIN IMMEDIATE`; `cadence.py#L118-L140` computes elapsed weekly 00:01 team-local boundaries with `max_intervals=256` and raises `CadenceInputError` if catch-up exceeds its 255-interval message. `cadence.py#L142-L188` compares existing rows, inserts missing cycles in number/boundary order, marks past rows completed, changes team active pointer and returns two Upcoming. Unique `(team_id, number)` and `(team_id, cadence_boundary_at)` constraints in `db.py` guard duplicate slots. Approved policy in `docs/team-cycle-cadence-plan.md#Decisions` requires bounded, atomic catch-up or an explicit error, never silent omission or partial success.

## Fixture

Two fresh rev12 SQLite DBs at `/tmp/hoja-cadence-cap/{cap,rollback}.db`, each seeded with its own organization/team and enabled with injected aware clock 2020-01-01 12:00 UTC. Baseline was exactly three rows (Current1 + Upcoming2/3) and a persisted team active pointer, read on a separate connection. `cap.db` will be reconciled at `start+258 weeks` (1806 days, >256 due boundaries); `rollback.db` at `start+20 weeks`, with a disposable SQLite trigger aborting a **later** cycle insert after earlier catch-up inserts begin. No original database, browser tab, or Linear account is touched. No unit-test files or runner.

## Cap

On `cap.db`, a controlled Writer reconciliation at `2020-01-01 12 UTC + 258 weeks` raised `CadenceInputError: Cycle catch-up exceeds 255 intervals; manual review is required.` The same invocation repeated gave the same error. Both fresh persisted reads still showed exactly original three rows and the original active pointer; **zero** catch-up rows were processed or committed because the function reaches the cap before inserts. This is the approved atomic-error policy, not partial batch continuation. A later invocation at +20 weeks (a **different, earlier clock input**, not continuation from +258) succeeded with Current21 and 23 total rows. This demonstrates the fixture is recoverable if an operator can address time/policy; repeated +258 invocations do **not** make progress and require manual review. No skipped/duplicate rows were claimed for the unprocessed 258-week horizon.


## Rollback

On disposable `rollback.db`, captured **all** cycle ID/number/start/end/completed/updated fields plus team active pointer/updated_at from a fresh connection (three baseline cycles). A SQLite trigger `BEFORE INSERT ON cycle WHEN NEW.number=11` aborted the real Writer reconciliation at +20 weeks, **after** catch-up inserts numbered 4–10 had begun within its `engine.begin()` transaction (`cadence.py#L165-L186`, `writer.py#L189-L200`). Writer raised `IntegrityError` containing the fixture marker. A fresh post-failure snapshot exactly equaled the pre-state: three cycles, original pointer, no timestamp churn. After dropping only the fixture trigger, retry at the same injected time produced Current21, exactly 23 contiguous unique cycle numbers, and no duplicates. This establishes SQLite transaction atomicity across cycle inserts and pointer/history updates for this failure; process termination, PostgreSQL, and a failure after commit were not simulated.


## Result

Both isolated checks matched the approved *bounded atomic* policy: >256-week catch-up failed explicitly before any write, with no progress on repeated far-time calls; a +20-week path completed Current21/23 rows. A late injected insert error rolled back every attempted catch-up row and team metadata, then a safe retry completed all due rows. No correctness defect was reproduced, so no product code/version edit was made. Final fresh reads found the cap fixture stable at 23 rows after its earlier +20-week recovery (the first far-time attempts had kept 3), and the rollback fixture stable at 23 on repeat. `python3 -m compileall -q cliniar_server` and `git diff --check` passed; only this new audit document was added this turn. Original DB, dirty work, browser tabs and Linear remained untouched; no unit tests. **Limitations:** cap policy requires manual review after >255 intervals and does not automatically batch/continue, and PostgreSQL/process-crash/multi-worker semantics were not checked.

