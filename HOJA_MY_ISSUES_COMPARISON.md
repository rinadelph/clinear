# My issues comparison

## Comparison

In the existing headed browser, authenticated Linear tab t2 showed `/cloverve/my-issues/assigned` and authenticated Hoja tab t1 showed `/workspace/my-issues/assigned`, each 1264px wide. Linear showed a 13px page title at y=23, pill tabs at y=61, a white list surface, compact row groups beginning with Urgent issues, Blocking issues, Cycle, Other active and Backlog. Hoja showed a 30px page title at y=97, tabs at y=201, a dark page surface, and only In Progress/Todo groups. Linear's Assigned view has collapse controls/counts, issue rows with ID/status/title and metadata, Add filter (Status, Priority, Project, etc.), Display options (Focus grouping, sub-grouping, column toggles), and a details toggle. Created and Subscribed displayed flat issue rows; Activity showed a dated group. Hoja's Created and Subscribed already filter by creator/subscriber, but Activity was always empty and Filter/Display options were inert. Hoja's Assigned used a 100-issue workspace query and filtered the loaded issues by viewer ID, so larger workspaces may be incomplete. Reference screenshot: ephemeral `/tmp/linear-my-issues-loaded.png`; Hoja before: `/tmp/hoja-my-issues-before.png`.

Source: `frontend/src/main.tsx` lines 9–29 define issue fields, GraphQL query, route/tab state and current-user filtering; lines 42–44 render the page; line 64 renders issue groups and rows. `frontend/src/styles.css` lines 65–66 style the view. The backend exposes `createdAt`, `updatedAt`, `cycle`, `assignee`, `creator`, `subscribers` and issue filtering (`cliniar_server/schema.graphql` lines 200–220 and 282–291). User data and exact issue titles are not copied into this evidence file.

## Implementation

`frontend/src/main.tsx` lines 9–15 request creation/update dates along with
existing issue relationships; lines 27–29 keep Assigned scoped to the viewer
and preserve view routes; lines 43–44 render page-specific tabs and the new
list. Lines 65–85 derive active Assigned items, status/priority-filtered rows,
focus/status groups and counts, collapsible headers, Created/Subscribed flat
lists and Activity grouped by last issue update. Activity explicitly says it
is not complete event history. Empty and no-match states differ and filters
clear without changing backend data. `frontend/src/styles.css` adds the
page-scoped light compact surface, title, 28px tabs, popovers, group headers,
row layout and small-screen overflow handling after line 160. `VERSION` and
`pyproject.toml` moved to 0.10.0 and `CHANGELOG.md` records the work.

## Verification

`npm run build --prefix frontend` passed (TypeScript/Vite), and `git diff
--check` passed. In the existing headed browser at 1264px, Hoja My issues
title measured y≈22 and tabs y=60, versus Linear title y=23 and tabs y=61.
Hoja Assigned showed one Backlog group with one issue; Created showed a flat
row and Activity a dated group with an explicit history limitation. Filtering
Assigned to In progress yielded zero rows and a no-match message; Clear
filters restored one row. Display options switched Focus to Status. Collapsing
Backlog hid its row but retained count 1, and expanding restored the row.
Activity route survived reload. Clicking the row navigated to the issue detail,
and its back button returned to My issues. At 390px, four tabs remained
available through horizontal scrolling and the document width did not exceed
the viewport; the tab scrollbar was subsequently hidden without hiding tabs.
Browser errors/console were empty in the checked Hoja tab and sampled GraphQL
requests were HTTP 200. Linear and Hoja tabs stayed open. No unit tests were
created or run.

## Result

The inspected My issues title/tabs and supported read-only list controls now
work in Hoja, but full 1:1 functionality is **not established**: Linear focus
grouping includes blocking relationships, exact cycle labels, issue selection,
many filter dimensions, configurable columns, details pane and full activity
history. Hoja's loaded query is capped at 100 workspace issues; local
current-user filtering may omit older items on larger installations. Dates
in Activity are issue-update approximations, not a full event feed. The
existing Hoja issue data differs from the authenticated Linear workspace;
row-for-row comparison is not meaningful. A backend query/pagination pass and
activity event feed are needed for parity.
