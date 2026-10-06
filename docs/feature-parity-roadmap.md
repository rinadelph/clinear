# Hoja feature-parity roadmap

This is a proposed verification and sequencing plan, not a claim of complete
Linear parity. Earlier audits were taken from differing, dirty snapshots;
recheck current code and real browser flows before treating any item as a bug.

## Sequence

### P0 — Reconcile current behavior

- Inventory routes and API contracts against current source.
- Record loading, empty, partial, error, stale and unauthorized states.
- Exercise deep links, refresh, back/forward, keyboard and narrow viewport.

**Acceptance:** an evidence-backed route inventory and E2E browser smoke flow;
unsupported controls are hidden or explicitly unavailable.

### P1 — Core issue work loops

- Verify stable issue URLs, supported edits, comments, persisted state and
  failure feedback.
- Verify My Issues filters/pagination/activity and board handling of unknown
  statuses without dropping issues.

### P2 — Projects, cycles and initiatives

- Verify list/detail/create/update and issue associations against backed
  contracts; be honest about unsupported history, health and integrations.
- Verify cycle and initiative relationships, pagination and empty/error states.

### P3 — Inbox and Pulse semantics

- Extend notifications only from real recipient-scoped event sources, with
  durable read/archive and pagination semantics.
- Keep historical gaps and unavailable subscriptions visible; do not fabricate
  data to match reference screenshots.

### P4 — Administration and integrations

- Clarify workspace/member/team authorization and shared-view persistence.
- Implement optional GitHub and webhook features only after secret, tenancy,
  event and delivery contracts are decided; see `github-integration.md` and
  `webhook-support-design.md`.

## Definition of done

Every feature should preserve tenant boundaries and generic product defaults,
have end-to-end user-visible verification for persistence and error states,
and document what remains unsupported. Apply repository version/changelog
rules to product changes. Do not add unit tests; use E2E tests only.

No delivery dates or product-owner priorities are established here. Reconcile
every cited audit with the checked-out baseline before implementation.
