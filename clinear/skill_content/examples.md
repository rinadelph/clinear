# clinear — Examples

Copy-pasteable recipes. Each is a short, real shell snippet showing one concrete pattern.

## Auth & identity

```bash
# Quick health check — am I authed?
clinear me

# Detailed: which token source resolved?
clinear auth status

# One-time setup: scaffold config file
clinear init
```

## "Who am I and what am I working on?"

```bash
clinear me
clinear issue list --assignee me --state "In Progress"
```

## "Create an issue from a bug report"

```bash
clinear issue search "login broken on Safari" -n 5    # search first
clinear issue create --team CLO \
    --title "Login broken on Safari 17" \
    --description "Token refresh returns 401 only on Safari 17.x. Repro at https://app.example.com/login" \
    --priority 2 --label "bug,frontend"
```

## "What's in my queue today?"

```bash
clinear -o md issue list --assignee me --state "In Progress" --state "In Review" -n 20
```

## "Hand this off to Alice"

```bash
clinear issue assign CLO-35 "Alice"
clinear issue state CLO-35 "In Review"
clinear comment add CLO-35 "Handing off — see PR #1234 for context"
```

## "Move ten issues from label `bug-old` to `bug`"

```bash
clinear -o ids issue list --label "bug-old" -n 10 \
    | xargs -I{} clinear issue update {} --label "bug"
```

## "What did Bob ship this week?"

```bash
clinear -o md issue list \
    --assignee "Bob" --state Done \
    --updated-after $(date -d "7 days ago" +%Y-%m-%d) -n 50
```

## "Comment with the latest commit message"

```bash
git log -1 --pretty=%B | clinear comment add CLO-35
```

## "Comment with test output on failure"

```bash
if ! pytest; then
    pytest 2>&1 | tail -100 | clinear comment add CLO-35
fi
```

## "Current cycle progress" (raw)

```bash
clinear cycle current CLO
clinear -o json issue list --cycle current --team CLO \
    | jq 'group_by(.state.name) | map({state: .[0].state.name, count: length})'
```

## "Are there any blockers in the current cycle?"

```bash
clinear issue list --cycle current --team CLO --label "blocked"
```

## "Open the issue in my browser"

```bash
xdg-open "$(clinear issue url CLO-35)"
# macOS:
open "$(clinear issue url CLO-35)"
```

## "Daily standup template"

```bash
echo "## Yesterday"
clinear -o md issue list --assignee me --state Done --updated-after $(date -d "1 day ago" +%Y-%m-%d)
echo
echo "## Today"
clinear -o md issue list --assignee me --state "In Progress"
echo
echo "## Blockers"
clinear -o md issue list --assignee me --label "blocked"
```

## "Cycle review report"

```bash
TEAM=CLO
clinear cycle current $TEAM
echo
echo "### Done"
clinear -o md issue list --cycle current --team $TEAM --state Done
echo
echo "### In Progress"
clinear -o md issue list --cycle current --team $TEAM --state "In Progress"
echo
echo "### Blocked"
clinear -o md issue list --cycle current --team $TEAM --label blocked
```

## "Find the issue mentioned in this commit message"

```bash
ID=$(git log -1 --pretty=%B | grep -oE '[A-Z]+-[0-9]+' | head -1)
[ -n "$ID" ] && clinear issue get "$ID"
```

## "Create a sub-issue under a parent"

clinear v0.3 does not have a dedicated `--parent` flag for issue create. Use `raw query` as an escape hatch:

```bash
clinear raw query 'mutation { issueCreate(input: { teamId: "...", title: "Sub-task", parentId: "..." }) { success issue { identifier } } }'
```

## "Search for all issues mentioning a substring"

```bash
clinear issue search "rate limit"
```

## "List labels for a team"

```bash
clinear label list --team CLO
```

## "Get the URL of every high-priority unassigned issue"

```bash
clinear -o ids issue list --priority 1,2 --no-assignee \
    | while read id; do
        echo "$id: $(clinear issue url $id)"
    done
```

## Anti-recipes (avoid)

```bash
# DON'T — fragile, parses human output
clinear issue list | grep "In Progress" | awk '{print $1}'

# DO — server-side filter + JSON
clinear -o ids issue list --state "In Progress"

# DON'T — write a Python wrapper
# python -c "import requests; requests.post('https://api.linear.app/graphql', ...)"

# DO — use clinear in the shell
clinear issue create --team CLO --title "..."

# DON'T — print the token
# echo "Using token: $LINEAR_TOKEN"

# DO — verify silently
clinear auth status >/dev/null && echo "ok" || echo "auth failed"
```

## See also

- `overview.md` — when to reach for clinear
- `commands.md` — command-by-command reference
- `workflows.md` — longer multi-step patterns
- `filters.md` — server-side filter DSL
- `output-formats.md` — choosing `--output`
