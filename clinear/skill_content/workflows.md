# clinear — Workflow Patterns

Multi-step patterns that combine `clinear` commands. **Always chain via the shell.** Do not write Python wrappers — that's what the CLI exists to avoid.

---

## 1. Triage — claim unassigned issues

When a user says "triage Team CLO" or "clean up the inbox":

```bash
# Step 1 — list unassigned, recently created
clinear issue list --team CLO --no-assignee --state "Todo" -n 20

# Step 2 — for each issue you want to act on, get details
clinear issue get CLO-42

# Step 3 — assign + label + (optionally) move state
clinear issue assign CLO-42 me
clinear issue update CLO-42 --label "infra"
clinear issue state CLO-42 "In Progress"
```

**Behavioral rule:** during triage, never bulk-modify without showing the user the list first (with `-o human`). Confirm intent before mutations.

---

## 2. Daily standup — what am I working on?

```bash
clinear issue list --assignee me --state "In Progress" -n 20
clinear issue list --assignee me --state "In Review" -n 20
```

Render in markdown for the user:
```bash
clinear -o md issue list --assignee me --state "In Progress"
```

---

## 3. Create an issue from an error trace

When the user pastes a stack trace and says "log this":

```bash
# Step 1 — search first to avoid duplicates
clinear issue search "TypeError viewer" -n 5

# Step 2 — if no match, create
clinear issue create \
    --team CLO \
    --title "TypeError: viewer is undefined on /dashboard" \
    --description "$(cat error.log)" \
    --priority 2 \
    --label "bug"
```

**Behavioral rule:** ALWAYS search before create unless the user has explicitly said "create a new one even if duplicates exist."

---

## 4. Cycle health — what's at risk in the current sprint?

```bash
# Step 1 — what cycle are we in?
clinear cycle current CLO

# Step 2 — issues in current cycle, grouped by state
clinear -o json issue list --cycle current --team CLO | jq 'group_by(.state.name) | map({state: .[0].state.name, count: length, items: map(.identifier)})'

# Step 3 — blockers
clinear issue list --cycle current --team CLO --label "blocked"
```

---

## 5. Hand off an issue to another teammate

Three commands, in order, with one comment trail:

```bash
clinear issue assign CLO-35 "Bob"
clinear issue state CLO-35 "In Review"
clinear comment add CLO-35 --body "Handing off to @bob — context: see PR #1234"
```

**Behavioral rule:** always add a comment when handing off. A bare reassignment without context creates ambiguity downstream.

---

## 6. Bulk re-label (xargs pattern)

To re-label every issue carrying a deprecated label:

```bash
# Step 1 — preview the target set
clinear -o ids issue list --label "old-name" -n 100

# Step 2 — for each id, run the mutation
clinear -o ids issue list --label "old-name" -n 100 \
    | xargs -I{} clinear issue update {} --label "new-name"
```

`-o ids` emits one identifier per line, perfect for `xargs`.

---

## 7. Investigate one issue end-to-end

```bash
# Full payload
clinear -o json issue get CLO-35

# Comments
clinear comment list CLO-35

# Related issues by label
LABEL=$(clinear -o json issue get CLO-35 | jq -r '.labels[0].name')
clinear issue list --label "$LABEL" -n 10
```

---

## 8. Create issue and link to a PR

```bash
ISSUE=$(clinear -o json issue create --team CLO --title "Add retry to API client" --priority 3 | jq -r '.identifier')
echo "Created $ISSUE"
echo "Linear: $(clinear issue url $ISSUE)"
# Now reference $ISSUE in your PR title or commit message:
# clinear convention: include the identifier in the branch name (e.g. CLO-35-add-retry)
```

---

## 9. Weekly review — what shipped?

```bash
clinear -o md issue list --assignee me --state "Done" --updated-after $(date -d "7 days ago" +%Y-%m-%d) -n 50
```

---

## 10. Comment from CI output

In a CI script, post failure details to the related Linear issue:

```bash
ISSUE_ID=$(git log -1 --pretty=%B | grep -oE 'CLO-[0-9]+' | head -1)
if [ -n "$ISSUE_ID" ]; then
    pytest 2>&1 | tail -50 | clinear comment add "$ISSUE_ID" --body -
fi
```

---

## Anti-patterns (do NOT do these)

| Don't | Why | Instead |
|---|---|---|
| Write a Python script calling Linear's GraphQL directly | clinear already handles auth/retries/pagination/validation | Use `clinear` in the shell |
| Loop in shell when filters would do the job | One API call vs N | Use `clinear issue list --filter ...` |
| `clinear issue list \| jq` to filter on team or state | Server-side filters are faster and produce smaller payloads | Use `--team`, `--state`, `--assignee` |
| Hardcode tokens in scripts | Leak risk | Use `$LINEAR_TOKEN` env var, never `--token <real>` |
| Use `raw query` for things the wrapper supports | Inconsistent errors, no Pydantic validation | Use dedicated commands |
| `clinear issue delete` | Does not exist | Use state transition or archive workflow |
| Bulk mutate without `--dry-run` first when uncertain | One typo = many bad writes | Always preview with `--dry-run` |

## See also

- `commands.md` — verb-by-verb reference
- `filters.md` — `issue list` filter DSL
- `examples.md` — short copy-paste recipes
