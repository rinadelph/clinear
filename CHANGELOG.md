# Changelog

All notable changes to clinear will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.1] — 2026-05-25

### Added

- **Project memory board** (`clinear memory`) — persistent project-scoped memory
  for agents. Every agent invocation should start with `clinear memory remind`
  to load forced behavioral rules and recent community learnings.
  - `memory remind` — print a formatted digest (forced rules + community context)
  - `memory list` — list all entries with metadata
  - `memory add --title "..." --body "..."` — add a community entry
  - `memory update <id>` — edit an existing entry
  - `memory remove <id>` — delete an entry
  - `memory heal --dry-run` — remove stale community entries (older than
    `heal_after_days`, default 30)
  - Storage: `.clinear/memory.yaml` in the git repo root (project-scoped)
  - Seeded with 5 forced rules: verify auth, search before create, use JSON
    for piping, dry-run on ambiguous mutations, read memory board first
  - Community entries auto-heal after 30 days; forced entries never expire
- Cron-ready: `clinear memory heal` can be scheduled daily to keep the board
  clean and relevant.

### Files Changed
- `clinear/memory_board.py` — storage layer (YAML read/write, heal logic)
- `clinear/commands/memory.py` — 6 subcommands
- `clinear/cli.py` — register `memory_app`
- `clinear/skill_content/overview.md` — add memory board rules

---

## [0.4.0] — 2026-05-25

### Added

- **Multi-account credential support** — manage multiple Linear accounts and switch
  between them automatically per workspace or via explicit `--account` flag.
  - New config schema: `[accounts.<name>]` sections with `token`, `token_env`,
    and auto-populated `org_name`.
  - Workspace-aware defaults: git repository roots can be mapped to specific
    accounts via `config.toml [workspaces]` or automatically detected.
  - New `clinear auth` subcommands:
    - `auth accounts` — list all accounts with default/workspace/current markers
    - `auth add <name> --token <token>` — add a named account (optionally
      verifies token against Linear API to populate `org_name`)
    - `auth switch <name>` — set global default account
    - `auth remove <name>` — remove an account
    - `auth workspace` — show current git repo workspace and mapped account
  - New global flag: `--account <name>` / `-a <name>` — one-off override for
    any subcommand.
  - Backward compatibility: existing `[auth]` sections auto-migrate to
    `accounts.default` on first load. Single-account behavior is preserved
    as fallback.
- **`clinear update`** — self-update command that checks PyPI for the latest
  version and runs the appropriate upgrade command (`pip install --upgrade` or
  `pipx upgrade`). Supports `--dry-run` and `--yes` flags. JSON output mode
  supported for agent consumption.
- New dependency: `tomli-w>=1.0` (required for writing config updates from
  `auth add/switch/remove` commands).

### Changed

- `config.py` — replaced single `AuthConfig` with `AccountConfig` and
  `AccountsConfig` dict. Added `resolve_account()` for workspace-aware
  account selection and `save_config()` for persisting config changes.
- `cli_state.py` — added `account_name` field to `CLIState` for tracking
  the active account.
- `cli.py` — added `--account` global flag and `update` command registration.
- `init.py` — updated config template to use multi-account schema.

---

## [0.3.1] — 2026-05-14

### Fixed

- `issue create --project` and `issue update --project` now accept project **slugId**
  (e.g. `24a5eb4e800e`) and project **name** in addition to the full UUID. Previously,
  passing a slugId (the short identifier shown in the Linear UI) caused an
  "Argument Validation Error" from the Linear API because the mutation's
  `projectId` field requires the full 36-char UUID. A new `_resolve_project_id`
  helper now resolves slugIds and names to canonical UUIDs before sending the
  mutation, matching the resolution pattern already used for teams, labels, and
  states.

---

## [0.3.0] — 2026-05-14

### Added

- **Agent skill bundle** at `skills/clinear/` — a Swarm/Claude-style skill
  (SKILL.md frontmatter + `references/*.md`) that teaches AI agents both the
  mechanics of the CLI and the *behavior* of working through Linear (when to
  search before create, when to use `--output json`, how to chain commands,
  safety rules, anti-patterns). Install with `bash skills/install.sh`.
- **`clinear-mcp` MCP server** — optional Model Context Protocol server
  exposing:
  - **1 tool** `clinear_guide(topic)` returning structured teaching content
    (`overview` / `commands` / `workflows` / `filters` / `output-formats`
    / `examples`).
  - **7 read-only resources**: `clinear://me`, `clinear://issue/{id}`,
    `clinear://team/{key}`, `clinear://project/{id_or_slug}`,
    `clinear://cycle/current/{team_key}`, `clinear://issues/mine`,
    `clinear://issues/team/{team_key}`.
  - **6 prompt templates**: `triage`, `daily_standup`, `create_from_error`,
    `hand_off`, `cycle_review`, `issue_investigate`.
- **By design no mutation tools** on the MCP server. Mutations happen via
  the `clinear` CLI in a shell — every tool/prompt response carries a
  reminder reinforcing this rule.
- `clinear/skill_content/` — canonical markdown source bundled inside the
  wheel via `[tool.hatch.build.targets.wheel.force-include]`. Single source
  of truth for both the skill bundle and the MCP server.
- New optional dependency extra: `pip install 'clinear[mcp]'` pulls in
  `mcp>=1.12.0`. Core install stays untouched for users who don't need MCP.
- New console script `clinear-mcp` (entry point of the MCP server).

### Changed

- Bumped version to 0.3.0.
- Updated User-Agent string emitted by `LinearClient` to `clinear/0.3.0`.

### Notes

- The MCP code is **lazy-imported**. Users who install `clinear` without the
  `[mcp]` extra are not affected; the `clinear-mcp` script prints a friendly
  install hint and exits 2 if invoked without the dep.
- ALL MCP server logging is routed to stderr to keep stdio JSON-RPC clean.

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
