# Next dogfood screen: project issue navigation

## Baseline

Authenticated local Hoja tab t1 at `http://127.0.0.1:8790/workspace/project/bb8dab20-52fb-4dcd-a14b-86db7238a3be` shows **Hoja product dogfooding** in started state, nine associated ENG-2–ENG-10 issues and one published Pulse update. ENG-9 (“Audit Inbox, Board, Cycles, Members, Views and Settings screens”) is still Todo, but a directly observed project-detail usability defect is more immediate: each project issue row is a plain DIV, not actionable. Authenticated external Linear t2 remains read-only; t4 isolated fixture stays open. The worktree contains extensive pre-existing dirty/untracked frontend, backend, docs and version changes; preserve them.

## Scope

Selected bounded improvement: make project issue rows open their existing issue-detail route, and provide native keyboard activation/focus. `frontend/src/main.tsx` line 43 passes `ProjectDetails` the already-loaded `issues` list but not `openIssue`; `ProjectDetails` at line 159 renders related issues via `related.map(i=><div className="issue-row" ...>)`. `openIssue` at line 20 already takes an Issue and calls `navigate('Issue detail', /workspace/issue/<identifier>/<slug>)`; the server-loaded Issue detail has loading/error states and its own Back action (`main.tsx` lines 22–27, 40). The Linear project overview offers an Issues tab, but its exact row behavior was not reliably observed during this pass, so this change is a local usability fix rather than a 1:1 parity claim. Acceptance: click and Enter on an issue row navigate to that exact issue's detail; browser Back restores the project and nine-row list, no mutation. Long titles retain wrapping; controls are labeled and visibly focusable. Loaded issues are limited by existing pagination, so do not assert a workspace-total count.

## Implementation

`frontend/src/main.tsx` lines 18–23 and 38–43 pass `onOpenIssue` from the project page to `ProjectDetails`, reuse the existing `openIssue` route, and remember the originating project ID so the Issue detail Back action can return to that project. `ProjectDetails` line 159 now renders native labeled `<button type="button" className="issue-row">` instead of non-interactive DIVs; no new mutation or persisted data changes. `frontend/src/styles.css` final project issue rules make buttons full width, hover/focus-visible, and wrap long text. Issue detail retains its existing server fetch, loading/empty/error states; its Back label says Project when entered from this project. Repeated activations can add history entries but do not mutate data. On direct issue URLs or a reload without remembered context, Back conservatively goes to My issues; browser history Back remains available. Do not claim all project issues are loaded if pagination has more pages.


## Verification

At local project `/workspace/project/bb8dab20-52fb-4dcd-a14b-86db7238a3be`, after reload all nine issue rows were native buttons with `Open ENG-n: …` names. Focusing ENG-9 and pressing Enter navigated to `/workspace/issue/ENG-9/audit-inbox-board-cycles-members-views-and-settings-screens`, displayed its exact title, and exposed **← Project**; clicking that returned to the project with nine rows. Focusing ENG-5 and pressing Enter likewise opened its exact issue detail. Native browser Back returned to the project; after reloading an issue directly, its Back label appropriately defaulted to **My issues** because the in-memory origin was unavailable. At 390px all nine row buttons remained visible with no document horizontal overflow. Browser error/console checks were empty, sampled GraphQL requests returned 200, and the served project URL returned HTML 200. No issue mutation was submitted. Note: an initial mouse click immediately after reload failed to navigate while the project page was still settling, so keyboard activation and a second issue were checked after readiness; no duplicate mutation was possible. No unit tests were added or run.


## Result

The selected local project-detail usability defect is fixed: nine formerly inert issue rows now navigate to the corresponding issue detail via mouse/keyboard, with a project-context Back action. Changed `frontend/src/main.tsx` (component and return context), `frontend/src/styles.css` (row focus/wrapping), `VERSION`, `pyproject.toml`, `CHANGELOG.md`, and this document; pre-existing dirty backend/docs/frontend changes were preserved. Frontend build and `git diff --check` passed; browser verification above established behavior. Version 0.15.1. External Linear remained read-only and the existing tabs remained open. Full ENG-9 six-screen audit, complete Linear parity, and a persisted return context across direct issue reload remain outside this scoped improvement; no commit or release was made.

