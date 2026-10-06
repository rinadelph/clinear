# Pending cadence enablement and navigation

## Trace

New isolated fixture `/tmp/hoja-cadence-pending/pending.db`, schema rev12, one authorized team Pending Team/PEN disabled with zero cycle rows, served at `localhost:8808`. Separate agent-browser session `cadence-pending` authenticated with a fixture API key read from a private `/tmp` file; no original Hoja or Linear tab/service used. In `frontend/src/main.tsx` `TeamCycleSettings` near line 236, a required weekday draft enables `teamCycleCadenceEnable(teamId,weekday)`. The submit guard blocks busy/loading/error/missing saved state. The mutation is org-scoped/admin-only in `resolvers.py#L339-L347` and committed in `writer.py#L154-L187`; success returns authoritative active/upcoming cycles. The component sets `saved` after response; it does **not** cancel an in-flight POST on navigation and has no mutation generation guard. Navigating away unmounts it, so a late React state update will not paint another team's page, but whether the server committed must be reconciled by returning/reloading rather than re-submitting blindly. Before action, settings showed Choose weekday and disabled Enable.

## Verification

In isolated `cadence-pending`, selected Thursday (weekday 3), focused Enable and pressed Enter **once**, then immediately used the form’s Back to Cycles button. Network capture contained one `EnableCadence` POST; team Cycles showed Cycle 1, 2 and 3 afterward. Returning to settings showed persisted “starts each Thursday / Current Cycle 1 / Upcoming Cycle 2, Cycle 3” with no enable form, and a full reload retained the same state. An independent fresh SQLite connection confirmed `cadence_enabled=true`, `cadence_weekday=3`, cycle numbers `[1,2,3]`. Sampled local GraphQL calls returned HTTP200; browser errors/console were empty. This navigation followed a successful POST quickly, but interception did not delay the mutation response: it proves persistence through ordinary immediate navigation, **not** a controlled late-response race or a failed-submit path. No blind repeat submission occurred.


## Safety

All writes are limited to the disposable `/tmp/hoja-cadence-pending/pending.db` and isolated `cadence-pending` browser. Existing `hoja-live` t1/t2/t4–t9 tabs, original `~/.local/share/cliniar/hoja.db`, external Linear and prior dirty source remain untouched. No unit tests.

## Result

No stale-state defect was demonstrated for ordinary rapid post-submit navigation: the server committed one cadence and reload displayed authoritative settings. No product code change or version bump was warranted. A truly pending/delayed mutation completion during route change and failure-after-dispatch still require controlled isolated interception and receipt reconciliation before claiming full race safety. Only this audit document was added; original DB, dirty work and existing tabs/Linear remained untouched. `git diff --check` passed; no unit tests, commit or release.

