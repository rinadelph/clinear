---
name: clinear
version: 0.3.1
description: Guide for using the `clinear` CLI to work through Linear issues, projects, cycles, and comments from the command line. Use when the user asks to triage, create, update, search, comment on, or move Linear issues; manage labels; inspect cycles, projects, or teams; or anything involving a Linear identifier like CLO-35 / ENG-123. Reinforces a "use Bash + clinear, do not write Python wrappers" workflow.
author: rinadelph
requires:
  bins: ["clinear"]
  auth: true
tags: [linear, cli, issue-tracker, project-management]
---

# clinear — Linear CLI Skill

Help the user interact with Linear from the command line using the `clinear`
CLI. `clinear` is a type-safe Python CLI that wraps the Linear GraphQL API
with Pydantic v2 validation, six output formats, and a filter DSL.

## Agent Guidance

Best practices and operational guidance for AI coding agents using `clinear`.

### Key Principles

- **Just run the command** — `clinear` handles auth, retries, rate limits,
  pagination, and validation. Don't pre-fetch token validity; if auth is
  broken, the first call will surface a clean `AuthError` (exit code 3).
- **Prefer the CLI over raw GraphQL** — every common operation has a
  dedicated subcommand (`clinear issue list`, `clinear issue get`,
  `clinear comment add`, etc.). Reach for these before constructing GraphQL
  queries. Use `clinear raw query` only as an escape hatch.
- **Use `--output json` (or `-o json`) for piping** — pipe through `jq` for
  filtering or projection. Human-readable output uses Rich tables that are
  hard to parse and may change visually between minor versions.
- **Filter at the API, not in shell** — `clinear issue list --assignee me --state "In Progress"`
  is faster and produces smaller payloads than `clinear issue list | jq`.
- **Identifiers are case-sensitive** — `CLO-35`, never `clo-35`.
- **Search before create** — `clinear issue search "<query>"` before
  `clinear issue create` to avoid duplicate issues.
- **`clinear issue delete` does NOT exist** — Linear has no hard delete via
  API. Use a state transition (`Canceled` or `Archived`).

### Design Principles

The `clinear` CLI follows conventions from well-known tools — if you're
familiar with them, the knowledge transfers directly:

- **`gh` (GitHub CLI) conventions**: `clinear <noun> <verb>` (e.g.
  `clinear issue list`, `clinear team get`). Flags: `-o`/`--output` for
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
- Prefer `clinear issue get <ID> -o json` over listing + filtering when you
  already know the ID.
- For multi-issue inspections, use `-o json` once and `jq` the result rather
  than calling `clinear` N times.

### Safety Rules

- **Never log or echo `$LINEAR_TOKEN`** — the CLI redacts it automatically;
  don't undo that.
- **For destructive mutations, use `--dry-run` first** when the user's
  intent is ambiguous.
- **Comments are permanent** — `clinear comment delete` is reversible only
  in the Linear UI.
- **State transitions are server-validated** — passing an invalid state
  name returns an `InvalidInput` error (exit code 6) rather than silently
  doing nothing.

### Workflow Patterns

#### Triage unassigned issues
```bash
clinear issue list --team CLO --no-assignee --state Todo -n 20
clinear issue get <ID>
clinear issue assign <ID> me
clinear issue update <ID> --label "bug"
clinear issue state <ID> "In Progress"
```

#### Daily standup
```bash
clinear -o md issue list --assignee me --state "In Progress" -n 20
clinear -o md issue list --assignee me --state "In Review" -n 20
clinear -o md issue list --assignee me --label blocked -n 10
```

#### Create from error trace
```bash
clinear issue search "<key phrase from error>" -n 5
clinear issue create --team CLO --title "<title>" \
    --description "<error body>" --priority 2 --label "bug"
```

#### Hand off
```bash
clinear issue assign CLO-35 "Bob"
clinear issue state CLO-35 "In Review"
clinear comment add CLO-35 --body "Handing off — see PR #1234"
```

#### Cycle review
```bash
clinear cycle current CLO
clinear -o md issue list --cycle current --team CLO --state Done
clinear issue list --cycle current --team CLO --label blocked
```

#### Bulk re-label (xargs)
```bash
clinear -o ids issue list --label "old" -n 100 \
    | xargs -I{} clinear issue update {} --label "new"
```

→ Full workflow library: `references/workflows.md`

## Available Commands

### Identity / Auth
- `clinear me` — show the current user
- `clinear auth status` — check which token source resolved
- `clinear init` — scaffold `~/.config/clinear/config.toml`

### Teams
- `clinear team list`
- `clinear team get <KEY>` — e.g. `clinear team get CLO`
- `clinear team states <KEY>` — workflow states for a team
- `clinear team members <KEY>`

### Issues
- `clinear issue list [filters...]` — see `references/filters.md`
- `clinear issue get <ID>`
- `clinear issue create --team <KEY> --title "..." [--description ...] [--priority N] [--assignee NAME] [--label "a,b"]`
- `clinear issue update <ID> [--title ...] [--priority N] [--label ...]`
- `clinear issue state <ID> "<STATE_NAME>"`
- `clinear issue assign <ID> <USER>`
- `clinear issue prio <ID> <N>` (0=none 1=urgent 2=high 3=med 4=low)
- `clinear issue url <ID>`
- `clinear issue search "<text>"`

### Projects
- `clinear project list`
- `clinear project get <ID_OR_SLUG>`

### Cycles
- `clinear cycle current <TEAM_KEY>` — graceful empty (exit 0) when no cycle
- `clinear cycle list <TEAM_KEY>`

### Comments
- `clinear comment list <ISSUE_ID> [-n N]`
- `clinear comment add <ISSUE_ID> --body "..."` (or `--body -` for stdin)
- `clinear comment edit <COMMENT_ID> --body "..."`
- `clinear comment delete <COMMENT_ID>`

### Labels
- `clinear label list [--team <KEY>]`
- `clinear label create --team <KEY> --name "..." [--color "#hex"]`
- `clinear label delete <LABEL_ID>`

### Raw escape hatch
- `clinear raw query "<GraphQL string>"` — for one-off queries not yet wrapped

→ Full command reference: `references/commands.md`

## Global Options

All commands support:

- `--token <T>` — override env var (don't pass real tokens in scripts)
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

## Authentication

clinear resolves the Linear API token in this order:

1. `--token <T>` CLI flag
2. `$LINEAR_TOKEN` environment variable
3. `auth.token` in `~/.config/clinear/config.toml`

Verify the resolved source with `clinear auth status`. Tokens look like
`lin_api_<long-random-string>` — get one at https://linear.app/settings/api.

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
clinear issue get CLO-9999
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

clinear also ships an optional MCP server (`clinear-mcp`) that exposes the
same teaching content as an MCP tool, plus read-only Linear resources
(`clinear://issue/{id}`, `clinear://team/{key}`, etc.) and prompt templates
for common workflows. Install with `pip install 'clinear[mcp]'` and add to
your MCP client config:

```json
{
  "mcpServers": {
    "clinear": { "command": "clinear-mcp" }
  }
}
```

The MCP server is read-only by design. Mutations go through this skill's
`clinear` shell commands.
