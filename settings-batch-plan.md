# Complete Profile, Notifications, and Issue Labels Settings Batch

## Breakdown

### GraphQL/backend contracts
- **Need:** Valid unique SDL, resolver/store agreement, authenticated organization/user context, existing notification and label tables.
- **Expect:** Profile display name and notification preferences persist per user; inbox filtering respects preferences; labels are organization-scoped and admin mutations enforced.
- **Logic:** GraphQL request → authenticated context → resolver → store/database → payload. Invalid profile names/preferences fail safely; unauthorized label mutations do not write.
- **Breakpoints:** SDL duplicate fields/types, mismatched payload names, preference keys that differ from emitted event kinds, organization-scope mistakes, label CRUD authorization bypass.

### Frontend integration
- **Need:** Existing settings router, viewer state, workspace update callback, and GraphQL payloads.
- **Expect:** Profile updates the viewer display name only, email stays read-only; inbox preference toggles persist without implying email/push delivery; admins create/delete issue labels and members can view them.
- **Logic:** Navigation → settings page → query/mutation → updated local state and visible status. Failed mutations remain visibly failed.
- **Breakpoints:** Profile callback accidentally updates workspace state; UI payload selection mismatch; asynchronous query errors or stale state.

### Tests and verification
- **Need:** Disposable test database, backend test suite, frontend build, local browser harness if available.
- **Expect:** Coverage of profile validation/persistence, notification filtering and unread count, label CRUD/role boundaries, and browser persistence where supported.
- **Sequence:** inspect current code and state owners → fix integration/contracts → add focused tests → run focused tests → full backend suite/build/E2E → diff check and worktree review. No commits.
- **Breakpoints:** fixture violations (inbox events require existing issues), E2E harness dependency/runtime unavailable, existing uncommitted work must be preserved.

## Decisions
- Preserve all existing worktree changes and do not commit: resolved by user constraint.
- Keep current event model, API shape, and admin/member policy: resolved from existing code and agreed batch scope.
- No unresolved product decisions identified.

## Choreography / impact
1. Inspect resolver return payloads and parent viewer/workspace state. This determines the correct profile update path.
2. Correct profile state handling and any detected schema/resolver mismatches. Changes affect the settings component and its parent state only.
3. Verify store notification filtering and label mutations against current schema/table scope. These methods affect inbox and label settings queries/mutations.
4. Add targeted backend and browser coverage. Inbox test fixtures must create a real issue because `inbox_notification.issue_id` is non-null.
5. Run focused tests, full backend tests, frontend build, available E2E, and `git diff --check`; inspect status and leave uncommitted.
