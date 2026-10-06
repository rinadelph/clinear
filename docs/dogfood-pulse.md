# Local dogfood project and Pulse update

## Baseline

The authorized mutation target is authenticated local Hoja t1 at `http://127.0.0.1:8790/`, showing workspace **Hoja Test Workspace** and its Engineering team. Authenticated `https://linear.app/cloverve/pulse/all` in t2 is a read-only reference and receives no mutations. The isolated localhost:8801 fixture t4 is not the target. Existing browser tabs remain open. The local Projects page initially showed **No projects yet**; an independent SQLite read counted zero active projects, one ENG team and Backlog/Todo/In Progress/In Review/Done/Canceled team workflow states. The worktree is substantially dirty; no reset or commit is planned.

## Contract

`frontend/src/main.tsx` lines 161 and 135–138 provide New project and New issue forms; the latter takes team, status, project, title and description. GraphQL `projectCreate` and `issueCreate` are in `cliniar_server/schema.graphql` lines 72–82 and inputs at lines 322–353. `ProjectDetails` (`frontend/src/main.tsx` line 159) has a project **state** (backlog/planned/started/paused/completed/canceled), not a custom project-stage list. `workflow_state` belongs to a team (`schema.graphql` lines 130–139), with no stage-creation mutation. User confirmed using the existing team workflow states rather than implementing project-specific stages, and confirmed local Hoja rather than external Linear. Each project issue can be assigned an existing team workflow state. The Pulse feed only reads `projectUpdates` (`frontend/src/main.tsx` lines 71–94; `schema.graphql` line 56). No update-creation mutation or composer existed at inspection, so publication requires implementing and verifying that contract first. A failed or ambiguous submit must be reconciled by querying for the intended post before retrying; no blind duplicate submissions.

## Inventory

Observed remaining work, not a blanket assertion that all screens are unfinished: Pulse lacks publishing/composer, real For me/Popular ranking, subscriptions, comments/reactions and custom views (`docs/pulse-parity.md#Result`); My issues still lacks blocking graph, cloud-only agent/customer/revenue, historical activity import and details-pane parity (`docs/my-issues-parity.md#Remaining scope`); Agent shows an unconfigured-service state and Initiatives shows an unavailable placeholder (`frontend/src/main.tsx` lines 45–46). Projects are currently empty and Project details offer only metadata editing; the stage list is team-scoped, not project-scoped. Inbox, Board, Cycles, Members, Views and Settings are visibly navigable but have not been comprehensively audited in this task—track a screen-by-screen audit rather than inventing specific defects. Some Linear-only data integrations may remain explicit limitations, not promises of immediate parity.

## Project stages

In local **Hoja Test Workspace** with zero prior active projects, the New project UI created **Hoja product dogfooding**, description “Track and validate remaining Hoja screens through real local workflows; publish evidence-backed Pulse updates. Team workflow stages are used for issue status.”, attached to Engineering (ENG). The project detail URL is `/workspace/project/bb8dab20-52fb-4dcd-a14b-86db7238a3be`; project state was changed from backlog to **started** via Save project. After reload the heading, description and started select persisted; a local DB read confirmed exactly one active project with that name/state. Existing ENG workflow state names/order, independently observed as Backlog (0), Todo (1), In Progress (2), In Review (3), Done (4), Canceled (5), were not modified. These are **team issue stages**, not project-specific stages; user approved that choice. No validation/save error was observed. Do not claim a project-owned stage list.


## Screen work

Nine distinct issues were created through the local New issue UI, all attached to **Hoja product dogfooding** and ENG, with nonempty actionable descriptions from the observed inventory. After reload the project page displayed **Project issues 9** and nine rows. An independent read of the local database found exactly nine unique titles, matching the intended inventory, their expected state names, and nonempty descriptions; no duplicates. The first automated read immediately after a successful create returned count zero because the UI call completed before persistence became visible; checking later found ENG-3. Subsequent submissions were reconciled by a final read, not blindly retried.

| ID | Screen / work | Team issue stage |
| --- | --- | --- |
| ENG-2 | Pulse publish project updates from project screen | In Progress |
| ENG-3 | Pulse real For me/Popular ranking | Todo |
| ENG-4 | Pulse subscriptions/reactions/comments/custom views | Backlog |
| ENG-5 | My issues blocking relationships/details pane | Todo |
| ENG-6 | My issues cloud-only fields/history assessment | Backlog |
| ENG-7 | Initiatives placeholder → scoped workflow | Backlog |
| ENG-8 | Agent execution service contract | Backlog |
| ENG-9 | Audit Inbox, Board, Cycles, Members, Views, Settings | Todo |
| ENG-10 | Decide/implement project-owned stages | Backlog |

Issues are assigned to the approved **team** stages; no project-owned stages exist. The screen audit item intentionally does not claim defects in all six screens. Original ENG-1 stays outside this project. No failed submissions or missing items remain in the final nine-row check; individual issue-detail reload was not performed for every row, but project association/state/description were independently read from persisted records.


## Pulse update

The local project detail now has a separate **Post a project update** composer (`frontend/src/main.tsx` line 159, `styles.css` after the project-editor rules). It takes required Update body and Health (On track/At risk/Off track); the authenticated `projectUpdateCreate` mutation (`schema.graphql` lines 83,198,356; `writer.py` lines 439–458; `resolvers.py` lines 628–634) validates nonblank body, active same-workspace project, stamps actor/time and snapshots project progress. An isolated backend check passed before the original server was restarted to load the mutation. The original project already had nine verified issues and no prior project-update posts before submission. Draft text stated those confirmed facts, noted the in-flow editor save/reload and explicitly listed remaining work and unavailable project-owned stages. Health was **On track**. A first click did not produce a network mutation; the composer still held 508 characters and the DB had zero posts. Keyboard focus + Enter submitted once, returned “Project update published,” cleared the input and disabled Publish. An independent DB read then found exactly **one** 508-character update for this project, status `on track`. Navigating to `/workspace/pulse/all` showed one project card with the same opening text and “Project on track”; reload retained it. No second post was attempted after receipt. External Linear was not mutated.


## Verification

After a fresh reload of the local project detail URL, the heading remained **Hoja product dogfooding**, metadata state **started**, nine project issue rows, and the new project-update composer was available with empty required input. Pulse at `/workspace/pulse/all` showed exactly one newly published card for that project, its factually recorded body and **Project on track**, still present after reload; clicking its project link returned to the same project detail. Independent local DB reads counted one project, nine unique project-associated issues with expected ENG workflow state and nonempty details, and one 508-character project update. The local browser error/console checks were empty and sampled GraphQL requests returned HTTP 200; `/ready` reported ready. The external Linear tab remained open at its project overview, and t4 isolated fixture remained open. Submitting to external Linear was never attempted. The headed browser stayed open; only `hoja-web` was restarted once to load the new mutation. Pre-existing dirty repository changes were not reset. Frontend build, backend compilation, GraphQL schema build and `git diff --check` passed; no unit tests were added or run.


## Result

Local dogfooding now has one started project, nine actionable screen-work issues assigned existing ENG team stages and one real published Pulse update. This is not project-owned stage configuration; that unsupported product feature is tracked as ENG-10. The project editor now sits in document flow and the Pulse composer is separate from metadata editing. `VERSION` and `pyproject.toml` are 0.15.0 with a matching changelog. Remaining product work is recorded in ENG-2–ENG-10; full screen audits, exact Linear project editor parity, true Pulse For me/Popular/subscriptions/comments/reactions/custom views, and a project-owned stage model remain unimplemented or unverified. No repository commit, release or external Linear mutation was made.

