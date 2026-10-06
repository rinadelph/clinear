# Team cycle settings read-state audit

## Baseline

New isolated `/tmp/hoja-settings-switch/settings.db` (schema rev12), served only at `http://localhost:8806`, with one authenticated fixture organization/user and two distinguishable teams: Settings Alpha/SSA disabled (no cycles), Settings Beta/SSB enabled Friday in America/New_York. A new headed t9 tab was opened; original t1 database and tabs t1/t2/t4–t8 were not modified. `--open` was not used; the fixture token was provided to the login tool without printing it. Existing dirty worktree and AGENTS.md were inspected before edits. Linear t2 remains read-only.

## Contract

`frontend/src/main.tsx` `TeamCycleSettings` around line 236 owns `saved`, `weekday`, `busy`, `loading`, `error` and a `useEffect` keyed by `team?.id`. It queries `teamCycleCadence(teamId)` and commits result to `saved`/weekday only while a local `live` flag is true; cleanup flips `live` false on unmount/team change. A successful submit calls admin-only `teamCycleCadenceEnable`, then displays its authoritative response; failure shows error while draft remains. `App` routes `/workspace/team/<key>/cycles/settings` using the selected team key and provides viewer admin. `gql()` rejects GraphQL errors. Backend read is organization/team scoped (`resolvers.py` cadence query → Writer transaction), so unauthorized or missing team returns an error. A selection change should not show another team's previously saved status or unsaved draft, and a failed read should retain a retry route without implying a save.

## Reproduction

Ordinary navigation: t9 Alpha settings showed required blank weekday and disabled Enable. Selecting Tuesday changed only Alpha's unsaved draft. Clicking Beta team heading navigated `/workspace/team/ssb/home`; opening Beta settings showed **Settings Beta**, saved Friday/America-New_York/Current1/Upcoming2–3, with no Alpha Tuesday draft. Returning to Alpha showed blank weekday, so the draft was discarded on route remount; it had not persisted. Repeating with an unsaved Wednesday draft, direct Beta settings then Alpha settings again showed blank Alpha draft and correct headings. No ordinary stale success or error was reproduced. A controlled delayed A/B response was **not** produced by these ordinary navigations: no network interception was available in this pass, so the `live` guard is source evidence, not proof under an artificial race. No failed read was browser-induced yet.

## Implementation

No ordinary stale-data or cross-team result was reproduced: TeamCycleSettings unmounts on team heading navigation and its effect cleanup prevents a late result from committing after unmount. The unsaved weekday draft is intentionally discarded on navigation rather than silently saved. A missing team route displayed Team not found, never Beta's persisted status. No product edit is warranted from those observations. A failed authenticated read and controlled out-of-order A/B response were not yet induced, so the current effect guard is **not** claimed race-proof under all circumstances. The component currently has no explicit Retry button for a failed read; adding one without a reproduced error state would exceed this conditional repair task.


## Verification

Isolated headed t9 at `localhost:8806` revisited Alpha/SSA settings blank, selected an unsaved Monday draft, then opened Beta/SSB settings Friday/New_York; returning to Alpha showed blank (draft discarded) and no Beta status. A direct unknown-team `/workspace/team/missing/cycles/settings` displayed Team not found without a saved card. At 390×844 the Alpha route had zero document horizontal overflow and a visible topbar; its blank submit stayed disabled. Browser errors/console showed no error entries; sampled authenticated `8806/graphql` requests were HTTP 200. Exact settings route served HTML 200, `/ready` ready. A controlled late A/B response and forced failed browser read were not produced, so no claim about their rendered retry state. No unit tests or product code edits were made.


## Result

Ordinary team navigation, unsaved-draft disposal, persisted enabled status and missing-team handling behaved correctly in an isolated two-team fixture; no stale or failed read defect was reproduced that warranted a code change. The `live` effect guard was inspected but not independently challenged with a delayed response; failed-read retry UI remains unverified. Only this audit document was added during this turn; existing version/code remained unchanged. Original database, dirty work, headed tabs t1/t2/t4–t8 and read-only Linear were preserved, with an additional isolated t9. `git diff --check` passed; no unit tests/commit/release.

