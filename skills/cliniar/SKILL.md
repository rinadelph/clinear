---
name: cliniar
version: 0.7.0
description: Guide for using the `cliniar` CLI with Cliniar, Linear, or another Linear-compatible GraphQL service. Use for issue triage, creation, updates, search, comments, labels, cycles, projects, teams, and identifiers such as ENG-123. Reinforces a "use Bash + cliniar, do not write Python wrappers" workflow.
author: Cliniar contributors
requires:
  bins: ["cliniar"]
  auth: true
tags: [linear, cli, issue-tracker, project-management]
---

# Cliniar work-management skill

Help the user interact with Cliniar, Linear, or another Linear-compatible
GraphQL service from the command line using `cliniar`. Cliniar is generic,
self-hosted, offline-first, agent-native work management with Pydantic v2
validation, six output formats, and a filter DSL.

Use the canonical `cliniar`, `cliniar-mcp`, and `cliniar-serve` commands.
The `clinear*` aliases, legacy `CLINEAR_*` variables, and legacy `clinear`
config/data paths are deprecated one-release fallbacks. Do not use them in new
commands. Keep the wire-facing `LINEAR_TOKEN`, `LINEAR_API_URL`, and Linear
GraphQL names unchanged.

## Agent Guidance

Best practices and operational guidance for AI coding agents using `cliniar`.

### Key Principles

- **Just run the command** — `cliniar` handles auth, retries, rate limits,
  pagination, and validation. Don't pre-fetch token validity; if auth is
  broken, the first call will surface a clean `AuthError` (exit code 3).
- **Prefer the CLI over raw GraphQL** — every common operation has a
  dedicated subcommand (`cliniar issue list`, `cliniar issue get`,
  `cliniar comment add`, etc.). Reach for these before constructing GraphQL
  queries. Use `cliniar raw query` only as an escape hatch.
- **Use `--output json` (or `-o json`) for piping** — pipe through `jq` for
  filtering or projection. Human-readable output uses Rich tables that are
  hard to parse and may change visually between minor versions.
- **Filter at the API, not in shell** — `cliniar issue list --assignee me --state "In Progress"`
  is faster and produces smaller payloads than `cliniar issue list | jq`.
- **Identifiers are case-sensitive** — `ENG-35`, never `eng-35`.
- **Search before create** — `cliniar issue search "<query>"` before
  `cliniar issue create` to avoid duplicate issues.
- **`cliniar issue delete` does NOT exist** — Linear has no hard delete via
  API. Use a state transition (`Canceled` or `Archived`).

### Design Principles

The `cliniar` CLI follows conventions from well-known tools — if you're
familiar with them, the knowledge transfers directly:

- **`gh` (GitHub CLI) conventions**: `cliniar <noun> <verb>` (e.g.
  `cliniar issue list`, `cliniar team get`). Flags: `-o`/`--output` for
  format, `-n`/`--limit` for count, `-v`/`--verbose` for tracing.
- **`kubectl` conventions**: `--dry-run` previews mutations without
  executing.
- **Unix pipelines**: `-o ids` emits one identifier per line for use with
  `xargs`, `for`, or `while read`.

### Context Window Tips

- Use `-o ids` when you only need identifiers — avoids loading full issue
  payloads into context.
- Use `-n` to cap the result count (default is 50). For previews, use
  `-n 5` or `-n 10`.
- Prefer `cliniar issue get <ID> -o json` over listing + filtering when you
  already know the ID.
- For multi-issue inspections, use `-o json` once and `jq` the result rather
  than calling `cliniar` N times.

### Safety Rules

- **Never log or echo `$LINEAR_TOKEN`** — the CLI redacts it automatically;
  don't undo that.
- **For destructive mutations, use `--dry-run` first** when the user's
  intent is ambiguous.
- **Comments are permanent** — `cliniar comment delete` is reversible only
  in the Linear UI.
- **State transitions are server-validated** — passing an invalid state
  name returns an `InvalidInput` error (exit code 6) rather than silently
  doing nothing.

### Workflow Patterns

#### Triage unassigned issues
```bash
cliniar issue list --team ENG --no-assignee --state Todo -n 20
cliniar issue get <ID>
cliniar issue assign <ID> me
cliniar issue update <ID> --label "bug"
cliniar issue state <ID> "In Progress"
```

#### Daily standup
```bash
cliniar -o md issue list --assignee me --state "In Progress" -n 20
cliniar -o md issue list --assignee me --state "In Review" -n 20
cliniar -o md issue list --assignee me --label blocked -n 10
```

#### Create from error trace
```bash
cliniar issue search "<key phrase from error>" -n 5
cliniar issue create --team ENG --title "<title>" \
    --description "<error body>" --priority 2 --label "bug"
```

#### Hand off
```bash
cliniar issue assign ENG-35 "Bob"
cliniar issue state ENG-35 "In Review"
cliniar comment add ENG-35 "Handing off — see PR #1234"
```

#### Cycle review
```bash
cliniar cycle current ENG
cliniar -o md issue list --cycle current --team ENG --state Done
cliniar issue list --cycle current --team ENG --label blocked
```

#### Bulk re-label (xargs)
```bash
cliniar -o ids issue list --label "old" -n 100 \
    | xargs -I{} cliniar issue update {} --label "new"
```

#### Multi-account: let cliniar pick the right workspace
```bash
# One-time: declare which teams each account owns
cliniar auth add acme --token lin_api_xxx --teams "ENG,OPS"
cliniar auth add side --token lin_api_yyy --teams "SIDE"

# Now just use team keys / identifiers — the owning account is auto-selected:
cliniar issue list --team ENG     # → acme account
cliniar issue get SIDE-12         # → side account
cliniar --account acme me         # explicit override when needed
```

→ Full workflow library: `references/workflows.md`

## Available Commands

### Identity / Auth
- `cliniar me` — show the current user
- `cliniar auth status` — show the authenticated user + resolved token source
- `cliniar auth accounts` — list configured accounts (default/workspace/current/teams markers)
- `cliniar auth add <name> --token <T> [--teams "SWA,ENG"] [--default]` — add a named account
- `cliniar auth switch <name>` — set the global default account
- `cliniar auth teams <name> "SWA,ENG"` — set which team keys an account owns (for auto-selection)
- `cliniar auth remove <name>` — delete a named account
- `cliniar auth workspace` — show current git-repo → account mapping
- `cliniar init` — scaffold `~/.config/cliniar/config.toml`

### Teams
- `cliniar team list`
- `cliniar team get <KEY>` — e.g. `cliniar team get ENG`
- `cliniar team states <KEY>` — workflow states for a team
- `cliniar team members <KEY>`

### Issues
- `cliniar issue list [filters...]` — see `references/filters.md`
- `cliniar issue get <ID>`
- `cliniar issue create --team <KEY> --title "..." [--description ...] [--priority N] [--assignee NAME] [--label "a,b"]`
- `cliniar issue update <ID> [--title ...] [--priority N] [--label ...]`
- `cliniar issue state <ID> "<STATE_NAME>"`
- `cliniar issue assign <ID> <USER>`
- `cliniar issue prio <ID> <N>` (0=none 1=urgent 2=high 3=med 4=low)
- `cliniar issue url <ID>`
- `cliniar issue search "<text>"`

### Projects
- `cliniar project list`
- `cliniar project get <ID_OR_SLUG>`

### Cycles
- `cliniar cycle current <TEAM_KEY>` — graceful empty (exit 0) when no cycle
- `cliniar cycle list <TEAM_KEY>`

### Comments
- `cliniar comment list <ISSUE_ID> [-n N]`
- `cliniar comment add <ISSUE_ID> "<body>"` (body is POSITIONAL; omit to read stdin)
- `cliniar comment edit <COMMENT_ID> "<body>"` (positional; omit to read stdin)
- `cliniar comment delete <COMMENT_ID>`

### Labels
- `cliniar label list [--team <KEY>]`
- `cliniar label create --team <KEY> --name "..." [--color "#hex"]`
- `cliniar label delete <LABEL_ID>`

### Raw escape hatch
- `cliniar raw query "<GraphQL string>"` — for one-off queries not yet wrapped

→ Full command reference: `references/commands.md`

## Global Options

All commands support:

- `--token <T>` — override env var (don't pass real tokens in scripts)
- `--account <name>` / `-a <name>` — force a specific configured account
- `-o`/`--output {human,json,yaml,md,plain,ids}` — output format
- `-v`/`--verbose` — print GraphQL operations to stderr (token redacted)
- `-q`/`--quiet` — suppress non-essential output
- `--no-color` — disable ANSI colors
- `--dry-run` — print mutation payload without executing
- `--timeout <SECONDS>` — HTTP timeout (default 30)
- `--version` — print version and exit

## Output Formats

| Format | Use when |
|---|---|
| `human` (default) | Showing results in a terminal to a person |
| `json` | Piping to `jq`, parsing programmatically |
| `yaml` | Snapshots, configs |
| `md` | Pasting into PRs, chat, docs |
| `plain` | TSV for shell tools |
| `ids` | One identifier per line — feeds `xargs` |

→ Format deep dive: `references/output-formats.md`

## Authentication & Multi-Account

cliniar supports **multiple Linear accounts/workspaces** with no env-var
juggling — accounts live in `~/.config/cliniar/config.toml` and the right one
is selected automatically. You do NOT need to export a token per workspace.

### Set up accounts (one time)

```bash
cliniar auth add work     --token lin_api_xxx --teams "SWA,ENG" --default
cliniar auth add personal --token lin_api_yyy --teams "PER"
cliniar auth accounts          # see them, with [default]/[current]/teams markers
```

### How the active account is chosen (in order)

1. `--account <name>` / `-a <name>` — explicit override
2. **Team-key ownership** — if the command targets a team (via `--team SWA`
   or an identifier like `SWA-20`), the account whose `teams` list contains
   that key is chosen automatically. This is the "intelligent" path.
3. **Workspace mapping** — `[workspaces]` maps a git-repo root → account, so
   simply being inside a repo picks the right token. Inspect with
   `cliniar auth workspace`.
4. Global `default_account`
5. First configured account (fallback)

### Token resolution (within the chosen account, in order)

1. `--token <T>` CLI flag
2. `$<account.token_env>` environment variable (default `LINEAR_TOKEN`)
3. `token` stored in the account's config block (discouraged: plaintext)

Verify what resolved with `cliniar auth status` / `cliniar auth accounts`.
Tokens look like `lin_api_<long-random-string>` — get one at
https://linear.app/settings/api.

### Config schema (canonical — do NOT downgrade to `[auth]`)

```toml
[accounts.work]
token_env = "LINEAR_TOKEN"   # or: token = "lin_api_..."
teams = ["SWA", "ENG"]       # enables team-key auto-selection

[accounts.personal]
token = "lin_api_..."
teams = ["PER"]

[defaults]
default_account = "work"

[workspaces]
"/home/me/work/acme" = "work"
```

> The legacy single `[auth]` section is auto-migrated to `accounts.default`
> on load. Never hand-write `[auth]` — use `cliniar auth add` instead.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic error |
| 2 | Usage / typer arg error |
| 3 | AuthError — no token or rejected token |
| 4 | NotFoundError — issue/team/etc not found |
| 5 | NetworkError |
| 6 | InvalidInput — validation error |
| 7 | RateLimitError |
| 8 | APIError — GraphQL or server error |

Use them in shell scripts:
```bash
cliniar issue get ENG-9999
case $? in
    0) echo "ok" ;;
    4) echo "not found — that's expected" ;;
    *) echo "unexpected error" ; exit 1 ;;
esac
```

## See Also

- `references/commands.md` — full command-by-command reference
- `references/workflows.md` — multi-step patterns library
- `references/filters.md` — `issue list` filter DSL
- `references/output-formats.md` — choosing `--output`
- `references/examples.md` — copy-pasteable recipes

## Companion MCP server

cliniar also ships an optional MCP server (`cliniar-mcp`) that exposes the
same teaching content as an MCP tool, plus read-only Linear resources
(`cliniar://issue/{id}`, `cliniar://team/{key}`, etc.) and prompt templates
for common workflows. Install with `pip install 'cliniar[mcp]'` and add to
your MCP client config:

```json
{
  "mcpServers": {
    "cliniar": { "command": "cliniar-mcp" }
  }
}
```

The MCP server is read-only by design. Mutations go through this skill's
`cliniar` shell commands.

---

## Switching accounts ad-hoc

The config is multi-account by design (see Authentication above). To run a
single command against a specific account without changing the default:

```bash
cliniar --account personal issue list --team PER
# or pin a one-off token (not stored):
cliniar --token "lin_api_..." issue list --team SWA
```

If a command targets a team an account owns (`--teams`), the right account is
chosen for you — no flag needed.

## Bulk reassign issues from one user to me

```bash
# Find all issues by handle
cliniar issue list --team SWA --assignee deltaragaming 2>&1

# Reassign in a loop
for id in SWA-47 SWA-46 SWA-45; do
  cliniar issue assign "$id" me 2>&1
done
```

## Fetch full issue descriptions (for dashboards)

`-o plain` gives one-liners only. Use `-o json` + python3 for description:

```bash
cliniar --token "$TOKEN" -o json issue get SWA-50 2>/dev/null | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('Title:', d.get('title',''))
print('Description:', (d.get('description') or '')[:800])
"
```

## HTML issue dashboard

Generate a self-contained HTML board at a permanent path (not /tmp):
- `/home/swarm/Work/mono/swarm-board.html`
- Include: stats header, Mermaid dependency map, progress bars, issue cards with DoD checklists
- Serve: `python3 -m http.server 8888` then `register_deployment(port=8888)`

---

## WorkflowState enum — FIXED in 0.5.0

Older versions (≤0.4.x) crashed on teams that had a workflow state whose
`type` was outside the six documented categories (e.g. type `"duplicate"`):

```
error: List items did not match WorkflowState: 1 validation error for WorkflowState
type
  Input should be 'triage', 'backlog', 'unstarted', 'started', 'completed' or 'canceled'
```

This broke BOTH `cliniar team states <KEY>` AND `cliniar issue state <ID> "<NAME>"`.

**As of 0.5.0 this is fixed** — unknown state types pass through as plain
strings, so `team states` / `issue state` work normally. Just run the command:

```bash
cliniar team states SWA
cliniar issue state SWA-20 "Duplicate"
```

### Raw-GraphQL fallback (only needed on cliniar ≤0.4.x)

```bash
# 1. Get state IDs (raw bypasses the enum)
cliniar raw query 'query { team(id:"<TEAM_UUID>"){ states { nodes { id name type } } } }'
# 2. Get issue UUID
cliniar -o json issue get SWA-20 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])"
# 3. Transition
cliniar raw query "mutation { issueUpdate(id: \"<ISSUE_UUID>\", input: { stateId: \"<STATE_ID>\" }) { success issue { identifier state { name } } } }"
```

Note: `cliniar raw query "<STRING>"` needs the literal `query` subcommand first.

## cliniar comment add/edit: body is POSITIONAL, not `--body`

`cliniar comment add <ISSUE_ID> "<BODY>"` and
`cliniar comment edit <COMMENT_ID> "<BODY>"` — there is NO `--body` flag.
If the body argument is omitted, it reads from stdin (good for piping):

```bash
git log -1 --pretty=%B | cliniar comment add SWA-20
```

(Note: `cliniar memory add --title "..." --body "..."` is a *different*
command that DOES use `--body` — don't confuse the two.)
