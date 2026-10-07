# Hoja settings: information architecture and product proposal

## Purpose and status

This document proposes a coherent Settings area inspired by the information
architecture and density in the supplied Linear screenshot. It is a product
design proposal, not a claim that every listed control exists today. The
reference screenshot is used for layout and navigation cues only; Hoja's own
capabilities and access rules remain the source of truth.

**Observed in Hoja today:** Settings opens a distinct sidebar with Back to
workspace, My account, API keys, and (for admins) Workspace and Members. API
keys are personal, can be created/listed/revoked, and their secret is shown
once. Service connections have no backend model and are explicitly unavailable.
Workspace name/key and team creation are admin-only. Account settings currently
show account identity and role; there is not yet a complete profile,
notification, security, or preference persistence system.

**Proposed below:** categories and controls marked *Proposal* are future
information architecture. They should only become interactive when their
behavior, persistence, authorization, and tests are implemented. Until then,
show an honest unavailable/coming-later state or omit the control; do not render
fake toggles that imply saved behavior.

## Shell, sizing, and interaction

- Settings is a distinct full-height mode, replacing the app's normal sidebar
  and top search bar. Keep the current workspace context visible.
- Sidebar target: 236–252 px wide on desktop, full viewport height, independently
  scrollable. Main settings content scrolls independently. On narrow screens,
  present the settings navigation as a drawer with a clear close/back action.
- Sidebar top: **Back to app** returns to the exact prior route; below it a
  compact **Search settings…** field filters destinations. Search is a proposed
  local navigation filter, not global issue search.
- Use compact 28–34 px navigation rows; category labels are quieter than
  destinations. Keep a distinct selected row, visible keyboard focus, hover
  feedback, and accessible names. At the bottom retain the signed-in user and
  logout control. Do not add a product-news card or coding-agent control.
- Main content uses a readable max width around 760 px and generous outer
  margins. Use a page title, section headings, and compact grouped panels.
  Each setting row has a clear label, short explanation, and right-aligned
  control; use subtle separators, not an oversized form card per field.
- Save behavior must be explicit: persisted controls save immediately with
  success/error feedback, or grouped edits have Save/Cancel. Confirm destructive
  actions. Preserve unsaved form values when switching sections where practical.
- Every destination has a stable URL and browser back/forward support. Direct
  navigation to an admin-only destination still relies on backend authorization;
  hiding its link is not security enforcement.

## Sidebar map and proposed contents

### Personal

1. **Preferences** — *Proposal.* General startup/display preferences, first day
   of week, theme, font size, reduced motion, and issue/comment interaction
   defaults. Persist per identity/browser only after a storage contract is
   chosen; do not imply server sync before then. Theme selection can reuse the
   existing light/dark theme state if made available here.
2. **Profile** — *Proposal.* View/edit display name and avatar; email is
   identity-managed and should be read-only unless a verified email-change
   flow is added. Today only name/email/role are displayed in My account.
3. **Notifications** — *Proposal.* Per-event notification preferences and
   delivery channels. Hoja currently has inbox notification read/archive
   controls, but no complete preference or email-delivery contract.
4. **Code & reviews** — *Proposal.* Code-hosting review defaults and linked
   identity. Hide or label unavailable until a supported provider integration
   exists; do not accept provider tokens without secure storage and tests.
5. **Security & access** — *Proposal.* Active browser sessions, password
   changes, and sign-in policy. Only add actions backed by session/password
   lifecycle APIs; never claim session revocation until implemented.
6. **Connected accounts** — *Proposal/unavailable.* Provider linking state and
   disconnect actions require real OAuth/backend lifecycle. There are currently
   no connected-account records.
7. **Agent personalization** — *Proposal/unavailable.* User-controlled agent
   instructions, scoped memory preferences, and review/reset controls only if
   an agent service and data/privacy contracts are established. No agent
   personalization capability is currently configured.

### Issues

1. **Labels** — *Proposal.* Manage issue label names/colors and usage. Reuse
   existing issue-label create/delete APIs if they support the intended scope;
   confirm workspace/team ownership semantics before presenting editing UI.
2. **Templates** — *Proposal.* Issue templates with title, description, team,
   labels, and defaults. No template persistence/API is established.
3. **SLAs** — *Proposal/unavailable.* Define service-level rules, calendars,
   and breach behavior only after the issue timing/automation model exists.

### Projects

1. **Labels** — *Proposal.* Project-specific label catalog, separate from issue
   labels unless the data model explicitly unifies them.
2. **Templates** — *Proposal.* Reusable project setup, teams, and milestones;
   requires a template contract.
3. **Statuses** — *Proposal.* Project status names/order/color and transitions;
   use existing project states only if their contract supports administrative
   customization.
4. **Updates** — *Proposal.* Update cadence, health options, and reminder rules;
   publishing project updates exists separately from these settings.

### Features

1. **AI & Agents** — *Unavailable today.* Describe configuration only if an
   execution service can be securely connected and tested. The current Agent
   page says no execution service is configured.
2. **Loops** — *Proposal/unavailable.* Recurring workflow definitions, schedule,
   and pause/resume controls need a scheduler and persisted loop model.
3. **Initiatives** — *Proposal.* Default visibility, status/priority options,
   and ownership rules. Initiative CRUD exists, but global preference controls
   are not established.
4. **Documents** — *Proposal/unavailable.* Workspace document defaults and
   permissions require document storage and authorization.
5. **Customer requests** — *Proposal/unavailable.* Intake source, triage rules,
   and requester visibility require a request model.
6. **Releases** — *Proposal/unavailable.* Release naming, status, and automation
   require a release entity/workflow.
7. **Pulse** — *Proposal.* Update visibility and default view; do not claim
   subscriptions or ranking features that are explicitly unavailable.
8. **Asks** — *Proposal/unavailable.* Intake settings require an ask/request
   workflow and access model.
9. **Emojis** — *Proposal.* Custom emoji catalog only if upload, validation,
   storage, and permissions are implemented.
10. **Integrations** — *Unavailable today.* A catalog may explain planned
    providers, but show connected/disconnected status only from real persisted
    integration records. Do not collect credentials into a decorative form.

### Administration (workspace admins only)

1. **Workspace** — *Partially available.* Edit workspace name and key; keep
   these existing fields and server-side admin gate. Add workspace icon/URL
   only after storage and validation exist.
2. **Teams** — *Partially available.* Create teams with name and key. Team
   membership/workflow controls may be added only when supported and authorized.
3. **Members** — *Available.* View members, invite with copyable single-use
   links, and manage roles. Keep invite expiry, one-time use, and manual sharing
   expectations visible; email delivery is not provided.
4. **Security** — *Proposal.* Workspace sign-in and session policy; do not
   suggest SSO/MFA until implemented.
5. **API** — *Partially available.* Each user manages only their own API keys
   under Personal > API keys. Administration may document API behavior, but
   admins must not see another member's plaintext key or manage personal keys
   absent a deliberate authorization change.
6. **Applications** — *Proposal/unavailable.* OAuth clients, webhooks, or
   installed apps need actual models and secret lifecycle management.
7. **Billing** — *Out of scope/unavailable.* Hoja has no billing contract; omit
   rather than simulate invoices or plans.
8. **Usage & limits** — *Proposal.* Show measured limits only when real counters
   and enforcement semantics exist.
9. **Import & export** — *Proposal.* Export/import jobs need format, privacy,
   authorization, validation, progress, and failure/recovery contracts.

## Capability and safety boundaries

- **Currently supported:** personal API-key metadata/create/revoke; one-time
  secret reveal; workspace name/key updates; team creation; member listing,
  role management, and manual invite links. Existing backend auth is the
  enforcement layer.
- **Not currently supported:** service connection persistence, email invite
  delivery, complete profile/preferences/notification settings, billing,
  connected OAuth accounts, SSO/MFA, documents, releases, loops, and a configured
  agent execution service.
- A visible control is a promise. Until an API/storage/authorization contract
  exists, use read-only explanatory content or omit the destination. Never save
  credentials in local storage, expose stored key hashes, or imply a secret can
  be recovered after its one-time display.
- All changes must respect user/workspace scope, provide loading/empty/error and
  success states, and avoid losing data on uncertain mutation outcomes.

## Explicit omission

The reference screenshot's **What’s new / New controls for Linear coding
agent** card and related coding-agent control are intentionally omitted. Hoja
is not adding that news surface as part of this settings design.

## Suggested implementation sequence

1. Build the settings shell, search/filter navigation, URL sections, and Back to
   app using the real destinations: Preferences (clearly marked limited),
   Profile (read-only basics), API keys, Workspace, and Members.
2. Move existing controls into those sections without changing backend
   authorization; test admin and regular-member navigation.
3. Add preference/profile/notification APIs only after deciding persistence
   scope (browser vs identity/workspace), default values, and migration strategy.
4. Add each integration or feature destination only with a concrete backend,
   permission model, credential handling, tests, and recovery behavior.
