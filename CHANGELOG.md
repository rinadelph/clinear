# Changelog

All notable changes to clinear will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-05-14

### Added
- `clinear init` — scaffold the config file at `~/.config/clinear/config.toml`.
- `clinear comment` group: `list`, `add`, `edit`, `delete`.
- `clinear label` group: `list`, `create`, `delete`.
- Label resolution in `issue create` and `issue update` — accept label names
  (comma-separated) and resolve to UUIDs server-side per team.
- `VERSION` file at the repo root; `__version__` now reads from it.
- `CHANGELOG.md`.

### Changed
- `cycle current` now exits 0 with `{ "active_cycle": null }` (JSON) or
  a friendly message (human) instead of crashing with NotFoundError when
  a team has no active cycle.
- `issue search` results now render a full table with priority, state,
  assignee, and identifier columns.
- Bumped version to 0.2.0.

### Fixed
- 4 issues from the v0.1 smoke test:
  - `Issue.labels` / `Issue.subscribers` now flatten the GraphQL
    `{nodes: [...]}` connection wrapper automatically.
  - `searchIssues` no longer spreads the `Issue` fragment on
    `IssueSearchResult` (different GraphQL type).
  - YAML formatter no longer collapses nested object indentation.
  - Error exit codes propagate correctly through the typer entrypoint.

---

## [0.1.0] — 2026-05-14

Initial release.

### Added
- Core commands: `me`, `auth status/whoami`, `team list/get/states/members`,
  `issue list/get/create/update/state/assign/prio/url/search`,
  `project list/get`, `cycle current/list`, `raw query`.
- Pydantic v2 models for User, Team, Issue, Project, Cycle, WorkflowState.
- Async httpx GraphQL client with auth, retry, error handling, rate-limit
  awareness, and pagination helper.
- Six output formats: `human` (Rich tables), `json`, `yaml`, `md` (markdown),
  `plain` (TSV), `ids` (one identifier per line).
- Filter DSL for `issue list` covering team/state/assignee/project/cycle/
  label/priority/free-text/date filters.
- Token resolution from `--token` flag, `LINEAR_TOKEN` env var, or
  `config.toml`.
- Typed exit codes (0–8) for scriptable error handling.
- `--dry-run` for safe mutation previews.
- 28/29 passing E2E tests against the live Linear API.
