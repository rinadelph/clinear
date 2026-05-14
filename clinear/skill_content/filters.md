# clinear — `issue list` Filter DSL

Filters are applied server-side via Linear's `IssueFilter` GraphQL input. **Always prefer filters over post-hoc `jq` filtering** — server-side filters return less data, are faster, and are paginated correctly.

## All filter flags (combine freely)

```
--team <KEY>                  Team key (e.g. CLO). Repeatable.
--state <NAME>                Workflow state name. Repeatable.
--assignee <NAME|me>          Assignee name, display name, or 'me'.
--no-assignee                 Only unassigned issues.
--creator <NAME|me>           Issue creator.
--project <NAME|ID>           Project name or ID.
--cycle <current|ID>          'current' for active cycle, or cycle ID.
--label <NAME>                Label name. Repeatable or comma-separated.
--priority <N|N,N,...>        Priority levels (0=none 1=urgent 2=high 3=med 4=low).
--contains <TEXT>             Full-text match against title + description.
--created-after <DATE>        ISO date (YYYY-MM-DD) or RFC3339 timestamp.
--created-before <DATE>
--updated-after <DATE>
--updated-before <DATE>
--due-before <DATE>
--has-due-date                Only issues with a due date set.
--include-archived            Include archived issues (default: false).
-n, --limit <N>               Max issues (default 50).
--sort-by <FIELD>             Sort field: createdAt|updatedAt|priority.
--order <asc|desc>            Sort order.
```

## Composition rules

- All flags ANDed together: `--team CLO --state Done` = team is CLO AND state is Done.
- Repeated flags ORed within the same kind: `--state Todo --state "In Progress"` = state is Todo OR In Progress.
- Comma-separated values: `--priority 1,2` = priority is 1 OR 2.

## Common filter recipes

### My open work
```bash
clinear issue list --assignee me --state "In Progress" --state "In Review"
```

### Team backlog (Todo only)
```bash
clinear issue list --team CLO --state Todo -n 100
```

### High-priority bugs across the workspace
```bash
clinear issue list --label bug --priority 1,2 -n 50
```

### Stale issues — not touched in 30+ days
```bash
clinear issue list --updated-before $(date -d "30 days ago" +%Y-%m-%d) --state Todo
```

### Due this week
```bash
clinear issue list --due-before $(date -d "+7 days" +%Y-%m-%d) --has-due-date
```

### Recently created across team
```bash
clinear issue list --team CLO --created-after $(date -d "3 days ago" +%Y-%m-%d) --sort-by createdAt --order desc
```

### Free-text search inside a single project
```bash
clinear issue list --project "Q2 Roadmap" --contains "auth"
```

### Cycle blockers
```bash
clinear issue list --cycle current --team CLO --label blocked
```

### Issues I created but never assigned to anyone
```bash
clinear issue list --creator me --no-assignee
```

## When filters aren't enough

For complex predicates not expressible in the flags (e.g. "issues with parent X", "issues where description contains regex Y"):

1. **Try `clinear issue search`** for full-text needs.
2. **Fall back to `--output json | jq`** only for projections (selecting fields), not for filtering. Filter at the API; project in the shell.
3. **Last resort: `clinear raw query`** with a custom GraphQL query.

## Performance tips

- Always set `-n` to the smallest sensible value. Default is 50; use 10 for previews.
- Combine `--team` + `--state` early — they short-circuit a huge slice of the dataset.
- `--contains` is full-text and slower than identifier-based filters; pair it with `--team` when possible.

## See also

- `commands.md` — full command reference
- `workflows.md` — when to use which filter combo
- `output-formats.md` — pairing filters with `-o ids` for xargs pipelines
