# Hoja issue-detail UX audit against Linear Kit

## Summary

Hoja's issue click currently opens a narrow drawer in place. Linear Kit navigates to a dedicated full issue-detail page with a breadcrumb, issue toolbar, title/description, activity and comments stream, and a properties panel. Hoja's drawer makes the issue feel like a read-only preview rather than a place to work. Several controls in Linear Kit are also inert, so copy the interaction hierarchy, not its fake actions.

## Current Hoja behavior and gaps

- Clicking an issue calls `setSelected(issue)` and opens `IssueDrawer`; it does not navigate to the issue's URL route. Deep links and browser back therefore do not represent the selected issue.
- The drawer only fetches issue detail after opening, starts from a possibly stale list object, and silently ignores fetch failure.
- Description is saved only on blur; save failure is unreported and the text remains looking saved.
- Status selector offers only the issue's current state, so it cannot actually change to another state.
- Priority can be changed; team and assignee are read-only.
- Comments can be listed/created, but there are no loading/error/empty states, timestamps are not presented, and the submit button's loading flag is not tied to comment submission.
- Labels, project, cycle, subscribers, activity history, attachments, sub-issues, favorites, archive, copy URL/ID, and issue options are absent.
- Cards do not link to a stable issue URL.

## Linear Kit issue detail patterns worth adopting

From `vendor/linear-kit/src/lib/components/pages/IssueDetailPage.svelte`:

1. Dedicated detail route and project → identifier → title breadcrumb.
2. Compact toolbar for options, copy link/ID, and primary work action.
3. Main content column with editable-feeling title/description, activity timeline, comments, and composer.
4. Separate properties sidebar for status, priority, assignee, cycle, labels, and project.
5. Menus are anchored to property controls; in Hoja only wire controls that have real backend support.
6. Resolve the requested issue by its actual ID/identifier; never fall back to a different or first issue.

## Recommended implementation order

1. Make issue clicks navigate to `/workspace/issue/:identifier`; make route parsing load the issue by identifier and browser back/forward close/open correctly.
2. Replace drawer-first detail with a responsive full-page two-column layout; optionally retain a quick-preview drawer as a secondary action.
3. Make status selector query all workflow states for the issue's team and save via `issueUpdate`; keep selected state synchronized after success.
4. Improve description save with explicit Save/Cancel or debounced save plus saving/saved/error feedback.
5. Upgrade comments with initial loading, empty state, timestamps, submission state, and surfaced errors.
6. Add labels and project/cycle properties using already-supported data/mutations; add assignee only after a safe member selector is available.
7. Add attachments/sub-issues/activity/favorites/options only when corresponding backend behavior exists; otherwise do not expose fake clickable controls.

## Risk notes

- GraphQL has issue detail, update, comment, labels, projects, and cycles support, but there is no general activity-history or subscriber management query/mutation in the current SDL.
- The detail page must display only known fields and clearly represent unavailable fields; do not present an empty value as if a fetch succeeded.
- Keep GraphQL authentication and org-scoped backend enforcement; route identifiers are untrusted input.

## Evidence files

- Current implementation: `frontend/src/main.tsx` (`IssueDrawer`, issue list click handler)
- Reference implementation: `vendor/linear-kit/src/lib/components/pages/IssueDetailPage.svelte`
- Backend contracts: `cliniar_server/schema.graphql`
