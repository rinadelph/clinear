# cliniar — Examples

Copy-pasteable recipes. Each is a short, real shell snippet showing one concrete pattern.

## Auth & identity

```bash
# Quick health check — am I authed?
cliniar me

# Detailed: which token source resolved?
cliniar auth status

# One-time setup: scaffold config file
cliniar init
```

## "Who am I and what am I working on?"

```bash
cliniar me
cliniar issue list --assignee me --state "In Progress"
```

## "Create an issue from a bug report"

```bash
cliniar issue search "login broken on Safari" -n 5    # search first
cliniar issue create --team ENG \
    --title "Login broken on Safari 17" \
    --description "Token refresh returns 401 only on Safari 17.x. Repro at https://app.example.com/login" \
    --priority 2 --label "bug,frontend"
```

## "What's in my queue today?"

```bash
cliniar -o md issue list --assignee me --state "In Progress" --state "In Review" -n 20
```

## "Hand this off to Alice"

```bash
cliniar issue assign ENG-35 "Alice"
cliniar issue state ENG-35 "In Review"
cliniar comment add ENG-35 "Handing off — see PR #1234 for context"
```

## "Move ten issues from label `bug-old` to `bug`"

```bash
cliniar -o ids issue list --label "bug-old" -n 10 \
    | xargs -I{} cliniar issue update {} --label "bug"
```

## "What did Bob ship this week?"

```bash
cliniar -o md issue list \
    --assignee "Bob" --state Done \
    --updated-after $(date -d "7 days ago" +%Y-%m-%d) -n 50
```

## "Comment with the latest commit message"

```bash
git log -1 --pretty=%B | cliniar comment add ENG-35
```

## "Comment with test output on failure"

```bash
if ! pytest; then
    pytest 2>&1 | tail -100 | cliniar comment add ENG-35
fi
```

## "Current cycle progress" (raw)

```bash
cliniar cycle current ENG
cliniar -o json issue list --cycle current --team ENG \
    | jq 'group_by(.state.name) | map({state: .[0].state.name, count: length})'
```

## "Are there any blockers in the current cycle?"

```bash
cliniar issue list --cycle current --team ENG --label "blocked"
```

## "Open the issue in my browser"

```bash
xdg-open "$(cliniar issue url ENG-35)"
# macOS:
open "$(cliniar issue url ENG-35)"
```

## "Daily standup template"

```bash
echo "## Yesterday"
cliniar -o md issue list --assignee me --state Done --updated-after $(date -d "1 day ago" +%Y-%m-%d)
echo
echo "## Today"
cliniar -o md issue list --assignee me --state "In Progress"
echo
echo "## Blockers"
cliniar -o md issue list --assignee me --label "blocked"
```

## "Cycle review report"

```bash
TEAM=ENG
cliniar cycle current $TEAM
echo
echo "### Done"
cliniar -o md issue list --cycle current --team $TEAM --state Done
echo
echo "### In Progress"
cliniar -o md issue list --cycle current --team $TEAM --state "In Progress"
echo
echo "### Blocked"
cliniar -o md issue list --cycle current --team $TEAM --label blocked
```

## "Find the issue mentioned in this commit message"

```bash
ID=$(git log -1 --pretty=%B | grep -oE '[A-Z]+-[0-9]+' | head -1)
[ -n "$ID" ] && cliniar issue get "$ID"
```

## "Create a sub-issue under a parent"

cliniar v0.3 does not have a dedicated `--parent` flag for issue create. Use `raw query` as an escape hatch:

```bash
cliniar raw query 'mutation { issueCreate(input: { teamId: "...", title: "Sub-task", parentId: "..." }) { success issue { identifier } } }'
```

## "Search for all issues mentioning a substring"

```bash
cliniar issue search "rate limit"
```

## "List labels for a team"

```bash
cliniar label list --team ENG
```

## "Get the URL of every high-priority unassigned issue"

```bash
cliniar -o ids issue list --priority 1,2 --no-assignee \
    | while read id; do
        echo "$id: $(cliniar issue url $id)"
    done
```

## Anti-recipes (avoid)

```bash
# DON'T — fragile, parses human output
cliniar issue list | grep "In Progress" | awk '{print $1}'

# DO — server-side filter + JSON
cliniar -o ids issue list --state "In Progress"

# DON'T — write a Python wrapper
# python -c "import requests; requests.post('https://api.linear.app/graphql', ...)"

# DO — use cliniar in the shell
cliniar issue create --team ENG --title "..."

# DON'T — print the token
# echo "Using token: $LINEAR_TOKEN"

# DO — verify silently
cliniar auth status >/dev/null && echo "ok" || echo "auth failed"
```

## See also

- `overview.md` — when to reach for cliniar
- `commands.md` — command-by-command reference
- `workflows.md` — longer multi-step patterns
- `filters.md` — server-side filter DSL
- `output-formats.md` — choosing `--output`
