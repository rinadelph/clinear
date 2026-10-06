# Cadence settings read recovery

## Baseline

New isolated SQLite `/tmp/hoja-cadence-read-retry/retry.db`, schema revision 12, single authorized fixture team Retry Alpha/RTA, served at `localhost:8807` by its own `cliniar-serve` process. New **agent-browser session `cadence-retry`** has its own tab and login; pre-existing headed `hoja-live` tabs t1/t2/t4–t9 and services remain open and untouched. API-key login was provided from a private `/tmp` file without printing it; `--open` was not used. Original `~/.local/share/cliniar/hoja.db` and authenticated Linear were not accessed for writes. Existing dirty worktree and AGENTS.md were checked first.

## Reproduction

`frontend/src/main.tsx` `gql` near line 19 posts authenticated GraphQL and throws on HTTP errors or GraphQL errors; App startup loads viewer/teams/issues and other data. `TeamCycleSettings` near line 236 uses `team.id` to query `teamCycleCadence`, tracks `saved`, `weekday`, `loading` and `error`, and has a `live` cleanup guard on team change/unmount. It displays a form whenever saved is absent, even after a read error, and has **no read retry control**. A genuine Retry must call the same authenticated cadence query again; clearing the error alone is not a retry.

In `cadence-retry`, normal authorized login and settings page showed Retry Alpha with blank weekday and disabled Enable. Using the agent-browser `network route` on the **exact** `http://localhost:8807/graphql` and `--abort`, navigating from team Cycles to Cycle settings while app data was already loaded produced a captured `query Cadence($id:String!){teamCycleCadence...}` POST with no response and a visible local `Failed to fetch` alert. The form remained present despite unknown saved status, and no Retry button existed. Removing the interception and reloading recovered, but reload is not an in-page retry. An initial aborted full-page reload failed the *App startup Dashboard* query first and showed global `Couldn't load this workspace`, not an isolated settings read; it is not evidence for the local retry defect. Attempts to use the root `route` command were invalid CLI input; the supported syntax is `agent-browser network route`. No account data was changed.

## Implementation

The reproduced transient Cadence POST abort left a visible `Failed to fetch` message but no in-page recovery, so `frontend/src/main.tsx` `TeamCycleSettings` now has a **manual** Retry loading cycle settings control. Its click increments a read attempt; the effect makes a new authenticated `teamCycleCadence(teamId)` request. A generation counter plus the existing `live` cleanup gate prevents older success/error/finally callbacks from committing after a retry or team change. Pending clears only the prior read error; saved settings are retained, and weekday is hydrated only when the draft is blank to avoid clobbering an unsaved selection on retry. Enable stays disabled while loading, after a failed read, or until an authoritative `saved` response exists, preventing an unsaved draft from appearing committed. A rejected auth read shows its error and is not automatically retried; manual retry is omitted for the literal `Authentication required` message. Repeated clicks while pending are disabled/guarded and there is no unbounded automatic loop. A route change discards the draft as previously observed.


## Verification

In separate `cadence-retry` browser session, exact `http://localhost:8807/graphql` abort after startup produced a local Failed to fetch with Enable disabled. After removing interception, clicking the visible Retry control issued **one new captured Cadence POST** and cleared the alert; the disabled fixture returned its blank weekday/disabled Enable. On a second attempt, a Friday draft was selected before navigating away. Re-entering the settings page under abort discarded that prior route draft, showed error/disabled Enable; removing abort and retrying recovered blank draft (route-remount behavior, not preservation of an unsaved draft across navigation). A missing team and auth-expired terminal error were not induced in this isolated session. At 390×844 no horizontal overflow and navigation opener visible. Browser error capture was empty after recovery; sampled GraphQL request HTTP200, exact settings path HTML200 and `/ready` ready. Other headed tabs and services remained unchanged, Linear read-only. No unit tests added/run.


## Result

A genuine authenticated transient cadence settings read failure was reproduced; the former UI had no retry and showed a create form despite unknown saved state. The new Retry sends a fresh query, guards stale callbacks, disables Enable until success and recovers without page reload in the isolated browser. Version 0.21.2 is in `VERSION`, `pyproject.toml`, `CHANGELOG.md`; frontend build/backend compilation and `git diff --check` passed. **Remaining limits:** a controlled out-of-order A/B success sequence, auth-expiry and non-admin terminal error rendering, and retention of an unsaved draft across route navigation were not verified or promised. The original DB, existing dirty files/tabs/services and external Linear were preserved; no commit/tag/release.

