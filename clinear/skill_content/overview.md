# clinear — Overview

`clinear` is a type-safe command-line client for Linear (https://linear.app). Built on Pydantic v2 + httpx + Typer. Designed for humans, AI agents, CI pipelines, and shell scripts.

## When to reach for clinear

Use `clinear` via the **Bash tool** whenever a task touches Linear:

- Anything mentioning a Linear identifier like `CLO-35`, `ENG-123`, or `<TEAM>-<N>`.
- "Create / open / file / log / track an issue."
- "Assign / move / triage / comment on" an issue.
- "What's in the current cycle / sprint?"
- "Which Linear projects exist?"
- "Who is working on X?"
- Any request for status, backlog, label, or workflow state operations.

## Why CLI over raw API

- Auth, retries, rate-limit handling, pagination, and Pydantic validation are already implemented in `clinear`. You do not need to reproduce them.
- Mutation safety: `--dry-run` previews destructive operations.
- Composition: every command supports `--output {human|json|yaml|md|plain|ids}` so you can pipe to `jq`, `xargs`, or another shell command.
- Stability: the CLI's command surface is versioned and tested with 36+ end-to-end tests against the live API.

## Behavioral rules (read these before invoking)

1. **Verify auth first in a fresh shell:** `clinear me`. If it fails, stop and surface the auth error to the user before any mutation.
2. **Discover accounts before assuming defaults.** When working across multiple Linear organizations, run `clinear -o json auth accounts` to see available accounts and their org names. Use `--account <name>` for one-off switches or `clinear auth workspace` to verify auto-detection.
3. **Search before create.** `clinear issue search "<query>"` prevents duplicate issues. Always run this when the user says "create an issue about X" unless they already gave you an explicit identifier.
4. **Use `--output json` when piping or programmatically reading.** `--output human` is for terminal display only.
5. **Linear identifiers are case-sensitive.** Use `CLO-35`, never `clo-35`.
6. **Use `--dry-run` on mutations** when the user's intent is ambiguous or destructive.
7. **Prefer dedicated subcommands over `raw query`.** `raw query` is an escape hatch for unsupported GraphQL operations only.
8. **Chain via the shell, not Python.** For multi-step workflows (create + assign + comment), call `clinear` three times — do not write Python wrappers around the Linear API.
9. **Filter at the API, not in shell.** `clinear issue list --assignee me --state "In Progress"` is faster and cleaner than `clinear issue list | jq`.
10. **Never log or echo the token.** The CLI masks it automatically; do not print `$LINEAR_TOKEN` in your shell output.
11. **`clinear issue delete` does NOT exist.** Linear has no hard delete via API. Use a state transition (e.g., `cancel` or `archive` workflow state) instead.

## Command tree (one-liner reference)

```
clinear me                          # current user
clinear auth status                 # who am I authed as?
clinear auth accounts               # list all accounts
clinear auth add <NAME> --token <T>  # add an account
clinear auth switch <NAME>           # set default
clinear auth workspace              # show current workspace + mapped account
clinear init                        # write config file
clinear update                      # self-update from PyPI

clinear team list
clinear team get <KEY>              # e.g. CLO
clinear team states <KEY>           # workflow states for a team
clinear team members <KEY>

clinear issue list [filters...]
clinear issue get <ID>              # e.g. CLO-35
clinear issue create --team <KEY> --title "..." [--description ...] [--priority N] [--assignee NAME] [--label "a,b"]
clinear issue update <ID> [--title ...] [--description ...] [--priority N]
clinear issue state <ID> "<STATE_NAME>"     # e.g. "In Progress"
clinear issue assign <ID> <USER_NAME>
clinear issue prio <ID> <N>                  # 0=none 1=urgent 2=high 3=med 4=low
clinear issue url <ID>
clinear issue search "<text>"

clinear project list
clinear project get <ID_OR_SLUG>

clinear cycle current <TEAM_KEY>
clinear cycle list <TEAM_KEY>

clinear comment list <ISSUE_ID> [-n N]
clinear comment add <ISSUE_ID> --body "..."          # or pipe via --body -
clinear comment edit <COMMENT_ID> --body "..."
clinear comment delete <COMMENT_ID>

clinear label list [--team <KEY>]
clinear label create --team <KEY> --name "..." [--color "#hex"]
clinear label delete <LABEL_ID>

clinear raw query "<GraphQL string>"          # escape hatch
```

## Global flags

- `--token <TOKEN>` — override env var. Use only when needed.
- `--account <NAME>` — one-off account override. Run `auth accounts` first to discover names.
- `--output, -o {human,json,yaml,md,plain,ids}` — output format.
- `--verbose, -v` — log GraphQL operations to stderr (token redacted).
- `--quiet, -q` — suppress non-essential output.
- `--no-color` — disable ANSI colors.
- `--dry-run` — print mutations without executing.
- `--timeout <SECONDS>` — HTTP timeout (default 30).
- `--version` — print version.

## Exit codes (scriptable)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic error |
| 2 | Typer / usage error |
| 3 | AuthError — no token or rejected token |
| 4 | NotFoundError — issue/team/etc not found |
| 5 | NetworkError |
| 6 | InvalidInput — validation error |
| 7 | RateLimitError |
| 8 | APIError — GraphQL or server |

Use these in shell scripts: `clinear issue get CLO-9999 || [ $? -eq 4 ] && echo "not found"`.

## See also

- `commands.md` — full noun/verb breakdown with examples
- `workflows.md` — common multi-step patterns (triage, standup, hand-off)
- `filters.md` — `issue list` filter DSL
- `output-formats.md` — how to choose `--output`
- `examples.md` — copy-pasteable real-world recipes
