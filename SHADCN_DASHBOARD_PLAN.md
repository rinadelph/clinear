# Shadcn-style React dashboard redesign

## Choreography

1. **Establish frontend foundation**
   - Add a Vite React TypeScript app under `frontend/`.
   - Add Tailwind-compatible design tokens and local shadcn-style primitives.
   - Preserve the Python backend as the production host.
   - Depends on the approved React/Vite and build-into-Python decisions.

2. **Build the application shell**
   - Implement zinc light/dark theme tokens, violet accent, top command/search bar, workspace switcher, responsive sidebar, user menu, and mobile navigation.
   - Add route/view state for Inbox, My issues, Projects, Cycles, Board, Activity, Notifications, Settings, Members, and Permissions.
   - The shell becomes the shared dependency for all screens.

3. **Build core work-management surfaces**
   - Inbox/table with filters, search, status/priority badges, assignee, labels, project/cycle metadata.
   - Issue detail drawer/page with description, status, priority, assignee, comments, labels, and edit controls.
   - Create issue dialog using the existing `issueCreate` mutation.
   - Projects and cycles views, with graceful empty states where current GraphQL support is limited.

4. **Build kanban and administration surfaces**
   - Status columns with responsive cards and accessible move controls.
   - Activity and notification views backed by available data or explicit empty-state contracts.
   - Settings, members, and permissions screens that clearly distinguish implemented behavior from future controls.
   - Avoid pretending unsupported mutations work.

5. **Integrate and package**
   - Configure Vite dev proxy to `/graphql`.
   - Build frontend into `frontend/dist`.
   - Copy the built app into the Docker image and configure Python static serving/fallback routing.
   - Keep `/graphql`, `/health`, and `/ready` behavior unchanged.

6. **Verify**
   - Run frontend typecheck/build and backend tests.
   - Run Compose config validation and a production-like container smoke test.
   - Use a browser smoke test against the running preview for login, dashboard rendering, theme switching, create issue, detail drawer, and responsive navigation.
   - Inspect the actual served HTML/assets, not only build output.

## Low-level data flow

- Browser loads Python-served React static app.
- Token is read from local storage and sent as `Authorization: Bearer ...`.
- React query helpers send GraphQL requests to the same-origin `/graphql` endpoint.
- Responses are normalized into dashboard view models.
- Mutations invalidate/refetch affected lists and detail views.
- Python continues enforcing authentication and organization scoping.

## Breaking points and mitigations

- **No existing Node frontend:** add a self-contained package with pinned lockfile and a minimal dependency surface.
- **GraphQL subset:** screens must show accurate empty/limited states rather than invent unsupported backend behavior.
- **Static serving fallback:** route `/` and client-side paths to `index.html` without intercepting `/graphql`, `/health`, `/ready`, or assets.
- **Docker build size/time:** use a multi-stage build and copy only `frontend/dist` into the Python runtime image.
- **Theme/accessibility:** use centralized CSS variables, keyboard-focus styles, semantic buttons/dialogs, and contrast checks for both themes.
- **Preview drift:** verify the Docker-built artifact and the live tmux preview separately.

## Acceptance criteria

- React/Vite build passes with no TypeScript errors.
- Standard shadcn-like zinc light/dark dashboard is visible at the self-hosted URL.
- Sidebar and mobile navigation expose all requested product sections.
- Inbox/table, kanban, issue details, create issue, projects, cycles, settings, members, permissions, activity, and notifications have usable screens or honest empty states.
- Existing authenticated GraphQL issue creation still works.
- Docker Compose builds and serves the compiled frontend from the Python app.
- Backend regression suite remains green.
