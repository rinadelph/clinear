# Hoja sidebar comparison

## Comparison

Observed in the same existing headed browser, with authenticated Linear tab `t2` at `/cloverve/agent` and authenticated Hoja tab `t1` at `/workspace/projects`, both 1264px wide. Linear's sidebar starts at the top-left and is 244px wide; Hoja's starts below a 68px full-width toolbar and is 252px wide. The reference has a compact 28px workspace header at y=16, 28px navigation rows at x=12 (My issues y=60, Pulse y=89, Inbox y=118, Agent y=147), a section heading at y=192 followed by Initiatives, Projects and Views, then Favorites and Your teams. Hoja has a 76px duplicate workspace card at y=90, 40px navigation rows, uppercase Work/Workspace headings, a green active row, and a bottom account panel. Linear uses a light gray sidebar with dark text and a subtle gray active row. Hoja's screenshot was dark green. Reference screenshots were captured at `/tmp/linear-sidebar-reference.png` and `/tmp/hoja-sidebar-before.png` (ephemeral, not repository artifacts).

The user chose sidebar-first parity including the Linear-only entries, with honest placeholder destinations rather than fabricated full functionality. Existing Hoja Board, Cycles, Members and Settings destinations must remain reachable; workspace switch, search, issue creation, logout, active route and mobile navigation must remain functional. Source: `frontend/src/main.tsx` lines 16–43 define navigation, routes and sidebar; `frontend/src/styles.css` lines 1, 11–13 and 30–35 define shell/sidebar styling and responsive overrides.

## Implementation

`frontend/src/main.tsx` lines 16–17 and 39–44 now render the observed primary,
Workspace, Favorites and team sections; placeholder routes explain what has not
been implemented. Working Board, Cycles, Members and Settings move to More rather
than disappearing. Workspace switching/search/create/logout still use their
original handlers. `frontend/src/styles.css` lines 148–160 define the 244px
top-aligned rail, light surface, compact 28px rows, neutral selection, compact
workspace header and mobile overlay. Long workspace names and rows ellipsize;
sidebar scrolling preserves access to the footer at small heights. Existing
configuration/version files were already modified before this task; this task
advanced `VERSION` and `pyproject.toml` to 0.9.0 and added a changelog entry.
The Your teams section is generated from the current workspace's team data;
it does not hardcode the reference workspace's name.

## Verification

`npm run build --prefix frontend` passed (TypeScript and Vite), as did
`git diff --check`. In the existing headed browser at 1264px width, Linear
`https://linear.app/cloverve/agent` had a 244px sidebar starting at y=0 and
28px rows (My issues y=60, Pulse y=89, Inbox y=118, Agent y=147). Served Hoja
`http://127.0.0.1:8790/workspace/projects` had a 244px sidebar starting at
y=0 and 28px rows (My issues y=60, Pulse y=88, Inbox y=116, Agent y=144).
The 390px Hoja viewport showed a hidden 290px drawer until the navigation
button opened it; page width did not overflow. Clicking Board closed it and
opened `/workspace/team/eng/active`. Pulse opened `/workspace/pulse`, displayed
an explicit unavailable message and remained selected after reload. Projects
opened `/workspace/projects` with its actual project list/empty state. Search
opened the command palette; Escape dismissed it. Workspace menu exposed its
existing settings, members and logout entries. Create issue opened a modal;
Cancel dismissed it without submitting. The dynamic Engineering team link
opened `/workspace/team/eng/home` and was selected after reload. Hoja browser
errors/console were empty and the inspected GraphQL requests returned 200.
Both original browser tabs remained open. No unit tests were added or run.

## Result

Width, left-rail origin, compact row sizing, section order, light surface and
neutral selection now align closely with the observed Linear desktop sidebar.
This is **not pixel-identical**: Linear's icon artwork, exact row offsets
(up to 3px in the first four), collapsed group affordances, favorites data,
footer/help/plan controls and content-area styling differ. Hoja deliberately
keeps its working extra routes in More; Linear-only routes remain labeled
placeholders. No authentication or data mutations were performed during the
comparison; creation of an issue was canceled.
