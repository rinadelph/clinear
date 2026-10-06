# Isolated populated sidebar cycle verification

## Fixtures

Created a **disposable** SQLite DB at `/tmp/hoja-cycle-cross-team/cycles.db`, served at `http://localhost:8804` with its own API-key-authenticated browser tab t7. The original `~/.local/share/cliniar/hoja.db`, original t1 and Linear t2 were not modified. One organization/one authenticated user has two distinct teams Alpha (ALP) and Beta (BET). Each has active Cycle 1, upcoming Cycle 2, two issues linked to its active cycle and one linked to upcoming: six issues, four cycles total. The private token is in `/tmp/hoja-cycle-cross-team/token` and was supplied to the headed login without echoing it. The fixture uses explicit authentication, not `--open`; the latter is restricted to unambiguous one-org/one-user SQLite by `cliniar_server/README.md`.

## Source map

`frontend/src/main.tsx` `routeView` line 21 maps team routes; its ordering matters because both `/team/<key>/active` (Issues) and `/team/<key>/cycle/active` end in `active`. App's team-cycle fetch at lines 32–33 uses team ID plus `isActive`/`isNext` GraphQL filters; `TeamCyclePage` at lines 235+ queries issue rows by both team and cycle IDs and derives selected link from URL. `cliniar_server/store.py` `_resolve_cycle_ids` resolves active_cycle_id and next number per team; `resolvers.py` `r_cycles` wraps `store.cycles` through generic `_conn` (no real pagination metadata). The external Linear account was read-only and cannot define the local fixture values.

## Cycle check

Before repair, direct t7 `/workspace/team/alp/cycle/active` showed **Alpha issues**, including ALP Upcoming A, rather than its current cycle. Beta `/cycle/active` similarly showed Beta issues including upcoming. Upcoming links were correct: `/team/alp/cycle/upcoming` displayed ALP Upcoming and only ALP-3; `/team/bet/cycle/upcoming` displayed BET Upcoming and only BET-3. This was a genuine routing defect: `routeView` checked generic team paths ending `/active` before more specific `/cycle/active`.

After repair, t7 direct/reloaded Beta `/team/bet/cycle/active` selected Current and showed BET Current with exactly BET-1 and BET-2. Alpha `/team/alp/cycle/active` showed ALP Current with exactly ALP-1 and ALP-2 after its load completed; Alpha Upcoming showed only ALP-3. Clicking Upcoming then Current restored the expected Alpha two rows and selected label. A read immediately after navigation temporarily observed loading/zero rows; the subsequent accessibility snapshot confirmed settled data. No content claim is based on the immediate transient.

## Team check

Switching by URL between Alpha and Beta Current/Upcoming in the same authenticated fixture tab showed only the selected team's cycle and items **after settling**. A second observation exposed that clicking an unqualified `.team-cycle-links button:nth-child(1)` while on Beta actually clicked Alpha's first Current link; the sidebar contained two teams, so this selector was not a Beta-switch test. Clicking the Beta-scoped nested link explicitly routed `/workspace/team/bet/cycle/active`, selected Beta Current and rendered only BET-1/BET-2. Beta Current never showed ALP IDs when targeted correctly; Alpha Upcoming never showed BET IDs. The fixture includes two teams under one identity; no separate cross-organization authorization test was performed. Missing team/cycle and request failure states are source-backed but not all browser-forced in this fixture. No data was created on external Linear.

## Repair

The observed Current routing discrepancy justified one narrow `frontend/src/main.tsx` `routeView` change: match `/team/.../cycle/` **before** generic team `/active`. No new cycle data, GraphQL fields, or states were fabricated. Existing `TeamCyclePage` and its project/team filters remained unchanged. The apparent cross-team leak on Beta Upcoming → “Current” was a browser automation selector mistake (first team child), not a product defect: an explicit Beta-scoped click returned Beta Current with BET-only IDs. No second code change was made for that false alarm. Other dirty repository changes were preserved.

## Verification

After the route repair, direct authenticated t7 URLs in the same headed session produced this settled matrix: Alpha Current → ALP Current, ALP-1/ALP-2, selected Alpha Current; Alpha Upcoming → ALP Upcoming, ALP-3, selected Alpha Upcoming; Beta Current → BET Current, BET-1/BET-2, selected Beta Current; Beta Upcoming → BET Upcoming, BET-3, selected Beta Upcoming. Direct reload of Alpha Upcoming and Beta Current retained matching issues; targeted Beta nested Current selection reached Beta, not Alpha. No browser errors or console entries were reported; sampled `localhost:8804/graphql` calls were HTTP 200. The frontend build, backend compilation and `git diff --check` passed. No unit tests were added or run.


## Result

A populated two-team fixture exposed one real bug: `/team/<key>/cycle/active` was routed to generic team Issues, displaying upcoming issues among current work. `frontend/src/main.tsx` route matching now prioritizes the cycle path, and all four team/position combinations rendered the correct cycle and linked issue IDs in the headed browser. Version 0.20.2 is recorded in `VERSION`, `pyproject.toml` and `CHANGELOG.md`. An apparent cross-team leak was conclusively traced to a first-match browser selector and did not justify a second code edit. The isolated fixture is not the original Hoja tenant; the original DB and external Linear account were not changed. Existing dirty work/tabs t1/t2/t4/t5/t6 remained, with an additional isolated t7; no commit/tag/release. Forced network failures, more than 100 issues, and cross-organization authentication remain unverified. Remaining full-product features (cycle creation, shared views, Customers, Agent execution) are separate contracts, not fixed by this verification pass.

