# Hoja rebrand and Linear Kit-aligned dashboard

## Choreography

1. **Rebrand product-facing surfaces**
   - Replace Cliniar branding in README, web titles, login/dashboard copy, frontend package metadata, Docker-facing UI labels, and documentation with Hoja.
   - Preserve legacy Python package names, CLI aliases, environment variables, migration paths, and compatibility tests until a deliberate breaking-release migration exists.
   - Add a canonical Hoja storage key for browser local storage and migrate existing local keys once.

2. **Match Linear Kit navigation**
   - Rebuild the React sidebar from the vendored routing contract:
     - Pulse, Inbox, My issues, Agent, Workspace, Initiatives, Projects, Views
     - More
     - Your teams: Home, Issues, Cycles, Current, Upcoming, Projects, Views
     - promo/help/footer regions where they are meaningful for Hoja
   - Make every supported item clickable and use route/view state instead of dead buttons.
   - Keep unsupported sections honest with explicit empty/coming-soon states rather than fabricated data.

3. **Implement Linear Kit-style team kanban**
   - Add Active, Backlog, and All issues tabs.
   - Add horizontally scrolling status columns matching Linear Kit’s density and card hierarchy.
   - Group real GraphQL issues by workflow state.
   - Show issue identifier, title, priority, project, cycle, labels, assignee, and created date when available.
   - Add a grouped-list rendering mode for saved/filtered views where appropriate.
   - Keep issue creation and detail navigation connected to the existing local mutations/routes.

4. **Align dashboard chrome and data boundaries**
   - Adopt Linear Kit’s workspace switcher, command/search affordance, team expansion, compact toolbar, and design-token behavior.
   - Keep backend-specific transformations in typed React helpers rather than inside presentational markup.
   - Replace hardcoded “Cliniar”, “Personal workspace”, placeholder counts, and misleading names with Hoja or actual data.

5. **Verify and package**
   - Search product-facing source excluding intentional legacy compatibility/vendor paths.
   - Run frontend TypeScript/build checks, backend tests, Compose build/config checks, and production asset verification.
   - Browser-smoke login, workspace menu, Linear-style sidebar navigation, kanban tabs, column rendering, issue drawer, and create issue.
   - Document the deliberate legacy compatibility exceptions and the Linear Kit provenance.

## Breaking points

- A literal global replacement would break Python imports, package entry points, environment migration behavior, and existing compatibility tests; those remain intentionally legacy.
- Linear Kit is Svelte 5 and Hoja is React; only visual/layout/data-contract patterns should be adapted.
- Some Linear Kit pages depend on data Hoja does not yet expose; those need truthful placeholders, not fake counts.
- SPA navigation must not intercept `/graphql`, `/health`, `/ready`, or asset requests.
- Kanban state grouping must handle unknown workflow states without dropping issues.

## Acceptance criteria

- New product UI, page title, login, package metadata, and docs use Hoja.
- Legacy compatibility references are limited to explicitly documented migration/code paths.
- Sidebar and team navigation mirror the Linear Kit structure and controls are interactive.
- Kanban provides Active/Backlog/All issues views with real local GraphQL issue data grouped into status columns.
- Issue cards and grouped list use actual backend values with explicit fallbacks.
- Frontend build, backend tests, Compose checks, production asset verification, and browser smoke checks pass.
