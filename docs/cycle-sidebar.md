# Team cycle creation and scheduling contract

## Contract

Authenticated Linear t2 `/cloverve/team/CLO/cycles` (read-only) showed automatically numbered Cycles 22 Planned, 21 Upcoming, 20 Current. A cycle row's menu offered Edit cycle name and description, Change cycle dates, Favorite, Copy link, Subscribe to cycle calendar. The Upcoming detail exposed separate Change cycle start/end date buttons and a calendar popover with Cancel/Apply; Escape closed it. No explicit **Create cycle** control appeared in the observed list/detail or sidebar. No external mutation was performed, and these observations do not establish whether cycles are automatically generated from team scheduling preferences or manually created by an inaccessible admin screen. Therefore we cannot infer a create-form contract, recurrence defaults, timezone, overlap policy or permission matrix from this account.

## Source map

Hoja `cliniar_server/schema.graphql` Query exposes `cycles(filter,first,after)` and `cycle(id)`; Cycle has id/name/number/start/end/completed/progress/team. There is **no** `cycleCreate` or `cycleUpdate` mutation or corresponding Writer method. `cliniar_server/db.py` cycle has team/org IDs, number and timestamps, and team stores `active_cycle_id`; `store.py` resolves `isActive`/`isNext` by team and number. `frontend/src/main.tsx` `TeamCyclePage`, `TeamCyclesPage` and nested sidebar links display filtered cycles but do not schedule or create. Adding a local create action would require a new authorized transactional API and a verified status/cadence rule so an inserted cycle would not be misleadingly classified as Current/Upcoming. The original Hoja workspace has no cycles; the isolated t7 fixture contains two teams/two cycles per team but was seeded explicitly for browser verification, not created through a product UI.

## Create

**Blocked by the observed contract.** The Linear list showed numbered cycles and edit/date menus but no Create cycle entry. Hoja has no `cycleCreate` mutation, Writer method, admin permission check, or validated team scheduling model. `team.active_cycle_id` determines Current and cycle numbers determine Upcoming; inserting an ad hoc row without a verified cadence/status transition could display a cycle in the wrong sidebar slot. A draft-only button would falsely promise persistence. No code or data was changed for this task. To implement it responsibly requires a separately specified team scheduling policy (manual vs generated, timezone, recurrence/overlap, who may create) and an authorized transactional GraphQL mutation with stable receipt and validation.


## Sidebar create

No Create cycle control was added to Hoja's sidebar: there is no backed mutation or observed Linear sidebar create affordance to mimic. Current, Upcoming and team Cycles still route to real read-only views, including the isolated populated t7 fixture. This is intentional, not a silent failure; the user should not be given a dead button. When a supported mutation exists, the UI would need a team-keyed draft, disabled invalid/pending submission, cancellation and post-receipt navigation.


## Scheduling

Linear Upcoming detail exposed separate start/end date buttons and a picker with Cancel/Apply, and the list menu offered Change cycle dates. Hoja stores `starts_at`, `ends_at` and team `timezone`, but has no cycle update mutation, overlap validation, permission rule, recurrence settings or confirmed timezone conversion semantics. Editing dates would change an existing cycle and could overlap its neighbor; this task cannot safely implement a scheduling UI from a calendar snapshot alone. Existing cycle dates remain displayed read-only. Invalid/overlapping date, stale-write and permission checks require the missing server contract; no other cycle was rescheduled.


## Verification

Authenticated Linear t2 at `/cloverve/team/CLO/cycles` was inspected read-only: numbered Planned/Upcoming/Current cards and an Open menu with Edit cycle name and description, Change cycle dates, Favorite, Copy link, Subscribe to cycle calendar. Upcoming detail `/cycle/upcoming` had separate start/end date controls; opening a picker showed date cells, Cancel and Apply, and Escape dismissed it. No submission or change occurred. Current Hoja GraphQL schema/writer/resolvers were searched for cycle mutation fields and none exist; `Cycle` read fields and `team.activeCycle` were traced in source. Isolated t7 still showed correct populated Beta Upcoming after this no-edit assessment; original t1 database and all browser tabs remained untouched. `git diff --check` passed. No unit tests were added or run.


## Result

Cycle creation and scheduling are **not safely implementable as a cosmetic follow-up**: no observed Linear Create cycle UI and no Hoja create/update contract, scheduling cadence, validation or permission model. Rather than invent a button or modify real cycles, this pass documented the exact boundary and preserved the functioning Current/Upcoming sidebar. A future backend design decision is needed before creation/scheduling can be called finished. No code version bump was made because no product code changed; no commit/tag/release or data mutation.

