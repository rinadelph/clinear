# Hoja view audit

## Evidence inspected

- `frontend/src/main.tsx` — current React routing/view state and interactions
- `cliniar_server/schema.graphql` — available local GraphQL queries/mutations
- `vendor/linear-kit/src/lib/routing.ts` — reference navigation/pages
- `vendor/linear-kit/src/lib/components/pages/TeamIssueBoardPage.svelte` — reference kanban

## Broken or unfinished visible views

### Critical: navigation does not route to real pages

The sidebar changes a single `view` string, not the URL. Refreshing, deep-linking,
back/forward navigation, and opening issue/project links do not work. There is no
React router or route resolver.

### Placeholder-only views

These currently render the generic `Placeholder` component and do not implement
their named product surface:

- Pulse
- Agent
- Workspace
- Initiatives
- Projects
- Views
- More
- Home
- Cycles
- Settings
- Members
- Permissions
- Notifications

### Partially implemented views

- **Inbox:** real issue data, search, and state filter; missing notification/read
  state, comments/activity, pagination, and real inbox badge.
- **My issues:** renders the same unfiltered issue list as Inbox; it does not filter
  by current assignee.
- **Board/kanban:** has real issue grouping and tabs, but status grouping can omit
  issues with unknown/unloaded states; no drag/drop or issue state mutation; column
  actions are inert; no saved-view/list mode.
- **Issue drawer:** read-only; no status, priority, assignee, label, project, cycle,
  comment, archive, or edit mutations.
- **New issue:** create works, but there is no project/cycle/assignee/labels/state
  selection and no optimistic/error recovery UX.
- **Workspace switcher:** opens a local menu but Add workspace does nothing and the
  current “workspace” is inferred from the first team, not organization data.

## Dead or misleading controls

- Command/search bar is visual only; Cmd/Ctrl+K does nothing.
- Filters button does nothing.
- More button does nothing.
- Theme toggle works.
- Avatar has no user menu.
- Team add button has no action.
- Team overflow button has no action.
- Kanban column More and Plus buttons have no action.
- Notifications badge is hardcoded to `0` rather than backed by data.
- Unsupported pages describe themselves as “ready” instead of showing a clear
  unavailable/empty state.

## Backend capability gaps

The backend supports core issues, teams, workflow states, projects, cycles, labels,
comments, attachments, and issue mutations. It does not currently expose browser-
ready organization switching, saved views, notifications/read state, initiatives,
activity feed, workspace settings, member administration, permissions UI, or
browser sessions/password login.

## Priority order

1. Add URL routing and a real app shell so navigation/deep links work.
2. Implement issue detail editing/comments and proper My Issues filtering.
3. Finish kanban interactions: state updates, unknown-state handling, column actions.
4. Implement Projects, Cycles, and Team Home from existing GraphQL data.
5. Add command palette and functional filters.
6. Add browser session/auth and organization/member administration.
7. Only then implement Pulse, Notifications, Initiatives, Views, and Settings backed
   by real models; otherwise keep explicit unavailable states.
