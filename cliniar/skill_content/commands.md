# cliniar — Commands Reference

Every `cliniar` command follows `cliniar <noun> <verb> [args] [flags]`. This is `gh`-style and consistent across all groups.

## Identity & Auth

### `cliniar me`
Show the currently-authenticated viewer (you).
```bash
cliniar me                          # human-friendly card
cliniar -o json me                  # JSON for piping
```

### `cliniar auth status`
Print which token source resolved (env var, config file, --token flag).
```bash
cliniar auth status
```

### `cliniar auth accounts`
List all configured accounts with default/workspace/current markers and org names.
```bash
cliniar auth accounts               # human-readable list
cliniar -o json auth accounts      # structured for agent reasoning
```

### `cliniar auth add`
Add a named account. Optionally verifies the token against the Linear API to populate `org_name`. Use `--teams` to declare which team keys the account owns (enables automatic account selection) and `--default` to make it the global default.
```bash
cliniar auth add work --token $LINEAR_WORK_TOKEN --teams "ENG,OPS" --default
cliniar auth add personal --token $LINEAR_PERSONAL_TOKEN --token-env LINEAR_PERSONAL_TOKEN
```

### `cliniar auth switch`
Set the global default account.
```bash
cliniar auth switch work
```

### `cliniar auth teams`
Set which team keys an account owns. When a command targets one of these teams
(via `--team SWA` or an identifier like `SWA-20`), that account — and its token —
is selected automatically, with no `--account` flag needed.
```bash
cliniar auth teams work "ENG,OPS"     # set
cliniar auth teams work ""            # clear
```

### `cliniar auth remove`
Remove a named account.
```bash
cliniar auth remove work
```

### `cliniar auth workspace`
Show the current git repo workspace and which account is mapped to it.
```bash
cliniar auth workspace
```

### `cliniar init`
Generate a starter config at `~/.config/cliniar/config.toml`.
```bash
cliniar init                        # creates if missing
cliniar init --force                # overwrite existing
cliniar init --path /tmp/foo.toml   # custom location
```

## Teams

A Linear team has a `key` (e.g. `ENG`, `ENG`) used as the prefix in issue IDs.

```bash
cliniar team list                          # all teams
cliniar team get ENG                       # detail card
cliniar team states ENG                    # workflow states (Todo, In Progress, Done, etc.)
cliniar team members ENG                   # team membership
```

**Behavior:** before transitioning an issue's state with `cliniar issue state`, run `cliniar team states <KEY>` to learn the exact state name. State names are team-scoped and case-insensitive in lookup but stored as titled strings.

## Issues — list & read

```bash
# List filters (combine freely)
cliniar issue list --assignee me
cliniar issue list --team ENG --state "In Progress"
cliniar issue list --team ENG --label bug --priority 1,2
cliniar issue list --project "Q2 Roadmap"
cliniar issue list --cycle current --team ENG
cliniar issue list --contains "auth"            # title/description full-text
cliniar issue list --created-after 2026-05-01
cliniar issue list -n 20                         # limit

# Read one issue (returns title, description, state, assignee, labels, comments)
cliniar issue get ENG-35
cliniar -o json issue get ENG-35                 # full structured payload

# Get the URL only (useful for sharing in chat or commit messages)
cliniar issue url ENG-35

# Full-text search across the workspace
cliniar issue search "rate limit"
```

## Issues — create & mutate

```bash
# Create
cliniar issue create --team ENG --title "Fix login flow" \
    --description "Token refresh fails on Safari" \
    --priority 2 --assignee "Alice" --label "bug,p2"

# Update fields
cliniar issue update ENG-35 --title "Better title" --priority 1

# State transition (run `team states ENG` first to see valid names)
cliniar issue state ENG-35 "In Review"

# Assign
cliniar issue assign ENG-35 "Bob"
cliniar issue assign ENG-35 me                   # special-case for viewer

# Priority shorthand (0=none 1=urgent 2=high 3=med 4=low)
cliniar issue prio ENG-35 1
```

**Behavior:** Use `--dry-run` to preview the GraphQL payload without executing:
```bash
cliniar --dry-run issue create --team ENG --title "Test" --priority 3
```

## Projects

```bash
cliniar project list
cliniar project get <ID_OR_SLUG>
```

`<ID_OR_SLUG>` is the project's UUID or its slug (the URL-safe short identifier visible in the Linear web UI).

## Cycles (sprints)

```bash
cliniar cycle current ENG            # active cycle for team ENG
cliniar cycle list ENG               # all cycles
```

**Graceful empty:** if the team has no active cycle, `cliniar cycle current` exits 0 with a friendly message in human mode and `{"active_cycle": null}` in JSON mode. **Do not treat this as an error.**

## Comments

```bash
cliniar comment list ENG-35                  # all comments on an issue
cliniar comment list ENG-35 -n 10            # limit

cliniar comment add ENG-35 "Looks good"

# Or pipe from stdin
echo "Build broke at step 4" | cliniar comment add ENG-35

# Or from a command's output
git log -1 --pretty=%B | cliniar comment add ENG-35

cliniar comment edit <COMMENT_ID> "Updated"
cliniar comment delete <COMMENT_ID>
```

## Labels

```bash
cliniar label list                           # workspace-wide
cliniar label list --team ENG                # team-scoped

cliniar label create --team ENG --name "infra" --color "#3b82f6"
cliniar label delete <LABEL_ID>
```

Labels referenced by `cliniar issue create --label "bug,p2"` are resolved by **name** per team. Run `cliniar label list --team <KEY>` first to confirm spelling.

## Raw GraphQL escape hatch

For queries not yet wrapped by a dedicated command:

```bash
cliniar raw query 'query { viewer { id name email teams { nodes { key } } } }'
cliniar -o json raw query 'query { ... }'
```

**Behavior:** prefer the dedicated commands. `raw query` is for advanced or one-off needs only — it does not validate against Pydantic models and may surface inconsistent error shapes.

## Self-update

### `cliniar update`
Check PyPI for a newer version and upgrade cliniar (supports pip and pipx installations).

```bash
cliniar update                     # check + interactive confirm
cliniar update --dry-run           # show what would happen
cliniar update --yes               # skip confirmation
cliniar -o json update --dry-run  # structured output for agents
```

## Global flags (apply before any subcommand)

```bash
cliniar --token <T> ...              # override env var
cliniar --account <NAME> ...          # use a specific account (one-off override)
cliniar -o json ...                   # output format
cliniar -v ...                        # verbose to stderr
cliniar --dry-run ...                 # preview mutations
cliniar --timeout 60 ...              # HTTP timeout
cliniar --no-color ...                # plain output
cliniar --version                     # print version and exit
```

## See also

- `workflows.md` — multi-step patterns
- `filters.md` — `issue list` filter DSL deep dive
- `output-formats.md` — choosing `--output`
- `examples.md` — recipes
