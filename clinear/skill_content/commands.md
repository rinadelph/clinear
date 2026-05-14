# clinear — Commands Reference

Every `clinear` command follows `clinear <noun> <verb> [args] [flags]`. This is `gh`-style and consistent across all groups.

## Identity & Auth

### `clinear me`
Show the currently-authenticated viewer (you).
```bash
clinear me                          # human-friendly card
clinear -o json me                  # JSON for piping
```

### `clinear auth status`
Print which token source resolved (env var, config file, --token flag).
```bash
clinear auth status
```

### `clinear init`
Generate a starter config at `~/.config/clinear/config.toml`.
```bash
clinear init                        # creates if missing
clinear init --force                # overwrite existing
clinear init --path /tmp/foo.toml   # custom location
```

## Teams

A Linear team has a `key` (e.g. `CLO`, `ENG`) used as the prefix in issue IDs.

```bash
clinear team list                          # all teams
clinear team get CLO                       # detail card
clinear team states CLO                    # workflow states (Todo, In Progress, Done, etc.)
clinear team members CLO                   # team membership
```

**Behavior:** before transitioning an issue's state with `clinear issue state`, run `clinear team states <KEY>` to learn the exact state name. State names are team-scoped and case-insensitive in lookup but stored as titled strings.

## Issues — list & read

```bash
# List filters (combine freely)
clinear issue list --assignee me
clinear issue list --team CLO --state "In Progress"
clinear issue list --team CLO --label bug --priority 1,2
clinear issue list --project "Q2 Roadmap"
clinear issue list --cycle current --team CLO
clinear issue list --contains "auth"            # title/description full-text
clinear issue list --created-after 2026-05-01
clinear issue list -n 20                         # limit

# Read one issue (returns title, description, state, assignee, labels, comments)
clinear issue get CLO-35
clinear -o json issue get CLO-35                 # full structured payload

# Get the URL only (useful for sharing in chat or commit messages)
clinear issue url CLO-35

# Full-text search across the workspace
clinear issue search "rate limit"
```

## Issues — create & mutate

```bash
# Create
clinear issue create --team CLO --title "Fix login flow" \
    --description "Token refresh fails on Safari" \
    --priority 2 --assignee "Alice" --label "bug,p2"

# Update fields
clinear issue update CLO-35 --title "Better title" --priority 1

# State transition (run `team states CLO` first to see valid names)
clinear issue state CLO-35 "In Review"

# Assign
clinear issue assign CLO-35 "Bob"
clinear issue assign CLO-35 me                   # special-case for viewer

# Priority shorthand (0=none 1=urgent 2=high 3=med 4=low)
clinear issue prio CLO-35 1
```

**Behavior:** Use `--dry-run` to preview the GraphQL payload without executing:
```bash
clinear --dry-run issue create --team CLO --title "Test" --priority 3
```

## Projects

```bash
clinear project list
clinear project get <ID_OR_SLUG>
```

`<ID_OR_SLUG>` is the project's UUID or its slug (the URL-safe short identifier visible in the Linear web UI).

## Cycles (sprints)

```bash
clinear cycle current CLO            # active cycle for team CLO
clinear cycle list CLO               # all cycles
```

**Graceful empty:** if the team has no active cycle, `clinear cycle current` exits 0 with a friendly message in human mode and `{"active_cycle": null}` in JSON mode. **Do not treat this as an error.**

## Comments

```bash
clinear comment list CLO-35                  # all comments on an issue
clinear comment list CLO-35 -n 10            # limit

clinear comment add CLO-35 --body "Looks good"

# Or pipe from stdin
echo "Build broke at step 4" | clinear comment add CLO-35 --body -

# Or from a command's output
git log -1 --pretty=%B | clinear comment add CLO-35 --body -

clinear comment edit <COMMENT_ID> --body "Updated"
clinear comment delete <COMMENT_ID>
```

## Labels

```bash
clinear label list                           # workspace-wide
clinear label list --team CLO                # team-scoped

clinear label create --team CLO --name "infra" --color "#3b82f6"
clinear label delete <LABEL_ID>
```

Labels referenced by `clinear issue create --label "bug,p2"` are resolved by **name** per team. Run `clinear label list --team <KEY>` first to confirm spelling.

## Raw GraphQL escape hatch

For queries not yet wrapped by a dedicated command:

```bash
clinear raw query 'query { viewer { id name email teams { nodes { key } } } }'
clinear -o json raw query 'query { ... }'
```

**Behavior:** prefer the dedicated commands. `raw query` is for advanced or one-off needs only — it does not validate against Pydantic models and may surface inconsistent error shapes.

## Global flags (apply before any subcommand)

```bash
clinear --token <T> ...              # override env var
clinear -o json ...                   # output format
clinear -v ...                        # verbose to stderr
clinear --dry-run ...                 # preview mutations
clinear --timeout 60 ...              # HTTP timeout
clinear --no-color ...                # plain output
clinear --version                     # print version and exit
```

## See also

- `workflows.md` — multi-step patterns
- `filters.md` — `issue list` filter DSL deep dive
- `output-formats.md` — choosing `--output`
- `examples.md` — recipes
