# AGENTS.md — Contributing to clinear

> Guide for humans and AI agents who modify this codebase.

---

## TL;DR (the rules)

1. **Every change bumps the version.** Patch for bugfixes (0.3.0 → 0.3.1), minor for features (0.3.x → 0.4.0), major for breaking changes.
2. **Every change updates `CHANGELOG.md`** under a new version heading.
3. **Every change is tested.** Run `bash scripts/e2e-test.sh` before commit. All 36+ tests must pass.
4. **Every commit goes through the pre-commit hook.** No secrets, no `.log`, no `.env`, no `schema/linear-schema.json`.
5. **Every release gets a git tag (`vX.Y.Z`) and a GitHub release.** No exceptions.

---

## Architecture

```
clinear/
├── VERSION                    Source of truth for __version__
├── pyproject.toml             Build metadata (must match VERSION)
├── CHANGELOG.md               Keep-a-Changelog format
│
├── clinear/                   Package
│   ├── __init__.py            Reads VERSION
│   ├── cli.py                 Root Typer app, global flags, error wrapper
│   ├── cli_state.py           Per-invocation state container
│   ├── config.py              TOML config + token resolution
│   ├── client.py              Async httpx GraphQL client
│   ├── auth.py                Viewer caching
│   ├── filters.py             Filter DSL → IssueFilter GraphQL input
│   ├── output.py              Six output formatters
│   ├── errors.py              Typed exit codes
│   ├── models/                Pydantic v2 models (User, Team, Issue, ...)
│   ├── graphql/               Query/mutation strings + fragments
│   ├── commands/              One file per command group
│   ├── skill_content/         Canonical markdown for the agent skill (shipped in wheel)
│   │   ├── overview.md
│   │   ├── commands.md
│   │   ├── workflows.md
│   │   ├── filters.md
│   │   ├── output-formats.md
│   │   └── examples.md
│   └── mcp/                   Optional MCP server (`pip install 'clinear[mcp]'`)
│       ├── content.py         ClinearGuide Pydantic model + load_topic()
│       ├── resources.py       7 read-only resource handlers
│       ├── prompts.py         6 workflow prompt templates
│       └── server.py          FastMCP wire-up; entry point of `clinear-mcp`
│
├── skills/                    Agent skill bundle (installable into ~/.swarmos and ~/.claude)
│   ├── install.sh             Symlinks skills/clinear into both skill dirs
│   └── clinear/
│       ├── SKILL.md           Frontmatter + body (mechanics + behavior + safety)
│       └── references/        Symlinks → ../../clinear/skill_content/*.md
│
├── schema/
│   ├── linear-schema.json     2.3 MB introspection result (GITIGNORED)
│   └── schema-summary.json    Categorized summary (committed)
│
├── scripts/
│   ├── e2e-test.sh            Live API E2E test suite
│   ├── pre-commit.sh          Secret-blocking pre-commit hook
│   └── install-hooks.sh       Install pre-commit hook
│
└── tests/                     (TODO: pytest unit tests for v0.3)
```

### Data flow for any command

```
User CLI input
  └─► clinear.cli.app (Typer)
        └─► global flags resolved → cli_state.CLIState
              └─► subcommand handler (clinear/commands/*.py)
                    └─► clinear.client.LinearClient.execute_as()
                          ├─► httpx POST to api.linear.app/graphql
                          ├─► JSON → dict
                          └─► dict → Pydantic model (validation)
                                └─► clinear.output.render(model, fmt)
                                      └─► stdout
```

### Adding a new command

1. Pick the right file in `clinear/commands/` (or create one).
2. Add a Typer command with rich `--help` text.
3. Write the GraphQL string in `clinear/graphql/queries.py` or `mutations.py`. Use fragments from `fragments.py`.
4. If the response shape is new, add or extend a Pydantic model in `clinear/models/`.
5. Register the new command group in `clinear/cli.py` via `app.add_typer(...)`.
6. Add an E2E test case in `scripts/e2e-test.sh`.
7. Bump version. Update CHANGELOG.

### Adding a new model

```python
# clinear/models/your_entity.py
from clinear.models.base import Timestamped

class YourEntity(Timestamped):
    id: str
    name: str
    # use Field(alias="camelCase") for GraphQL → snake_case mapping
```

### Adding GraphQL fragments

Keep fragments **DRY** and **small**. One fragment per entity "view":
- `YourEntityCore` → fields included in lists
- `YourEntityFull` → extra fields included on detail views

```python
# clinear/graphql/fragments.py
YOUR_ENTITY_CORE = """
fragment YourEntityCore on YourEntity {
  id
  name
  createdAt
}
"""
```

---

## Development Workflow

### Setup

```bash
git clone https://github.com/rinadelph/clinear.git
cd clinear
bash scripts/install-hooks.sh        # MANDATORY — installs the secret-blocking pre-commit hook
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Day-to-day

```bash
# 1. Set your token (one-time per shell)
export LINEAR_TOKEN="lin_api_..."

# 2. Edit code

# 3. Smoke test live API
.venv/bin/clinear me

# 4. Full E2E suite (takes ~30s)
bash scripts/e2e-test.sh

# 5. Lint + type check
uv run ruff check clinear/
uv run mypy clinear/

# 6. Bump version (see "Versioning" below)

# 7. Commit (hook will refuse if you touch secrets)
git add -A
git commit -m "fix(issue): handle null state in IssueSearchResult"
```

---

## Testing

### E2E (live API — primary suite)

`scripts/e2e-test.sh` exercises every command against the real Linear API.

```bash
export LINEAR_TOKEN="lin_api_..."
bash scripts/e2e-test.sh
```

The script reads `LINEAR_TOKEN` from your env. **It does not contain any hardcoded tokens.** If you find one, that's a bug — fix it immediately and rotate the leaked credential.

Pass condition: `SUMMARY: N passed, 0 failed`.

### Unit tests (TODO — v0.3)

`tests/` is empty as of v0.3.0. Planned with `pytest` + `respx` (mocks httpx) + Pydantic fixture data.

---

## Versioning

We follow [Semantic Versioning](https://semver.org/):

| Bump | When |
|------|------|
| **Patch** `0.3.0 → 0.3.1` | Bugfixes, typo corrections, internal refactors with no behavior change. |
| **Minor** `0.3.x → 0.4.0` | New commands, new flags, new output formats. Backward-compatible. |
| **Major** `0.x → 1.0` (then `1 → 2`) | Removed/renamed commands, changed exit codes, changed default output. |

### Version bump checklist (every change)

1. Edit `VERSION` to the new number.
2. Edit `pyproject.toml` → `version = "X.Y.Z"` (must match `VERSION`).
3. Add a new section to `CHANGELOG.md`:
   ```markdown
   ## [X.Y.Z] — YYYY-MM-DD

   ### Added
   - ...

   ### Changed
   - ...

   ### Fixed
   - ...
   ```
4. Run the E2E suite. Must pass.
5. Commit with message: `release: vX.Y.Z`.
6. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z"` and push: `git push origin vX.Y.Z`.
7. Create GitHub release (see Release Process).
8. Publish to PyPI (see Release Process).

---

## Release Process

### 1. Pre-flight

```bash
# Tests pass?
bash scripts/e2e-test.sh

# Lint passes?
uv run ruff check clinear/

# Version is bumped in BOTH places?
cat VERSION
grep '^version =' pyproject.toml

# CHANGELOG has the new section?
head -20 CHANGELOG.md
```

### 2. Tag and push

```bash
git add -A
git commit -m "release: v0.3.0"
git push origin main

git tag -a v0.3.0 -m "v0.3.0"
git push origin v0.3.0
```

### 3. Build with uv

```bash
rm -rf dist/
uv build
# → dist/clinear-0.3.0-py3-none-any.whl
# → dist/clinear-0.3.0.tar.gz
```

### 4. Publish to PyPI

```bash
# Token MUST come from environment — never paste into a shell that gets logged.
export UV_PUBLISH_TOKEN="pypi-..."
uv publish
```

### 5. Create GitHub release

```bash
gh release create v0.3.0 \
    --title "v0.3.0" \
    --notes-file <(awk '/^## \[0.3.0\]/,/^## \[/{if (!/^## \[/) print; if (/^## \[/ && !found) found=1; else if (/^## \[/) exit}' CHANGELOG.md) \
    dist/clinear-0.3.0-py3-none-any.whl \
    dist/clinear-0.3.0.tar.gz
```

### 6. Verify

```bash
# Wait ~60s for PyPI to propagate, then:
uv tool install --refresh clinear
clinear --version  # should print the new version
```

---

## Pre-commit Hook

`scripts/pre-commit.sh` is installed via `bash scripts/install-hooks.sh`. It runs on `git commit` and **refuses** to commit any staged file that contains:

- Linear API tokens (`lin_api_...`)
- PyPI API tokens (`pypi-...`)
- AWS access keys (`AKIA...`)
- GitHub PATs (`ghp_`, `ghs_`, `gho_`, `ghu_`, `ghr_`)
- Google service account JSON
- SSH/PGP private keys
- Slack tokens

It also blocks these file types entirely:
- `*.log`
- `.env`, `.env.*`
- `schema/linear-schema.json` (regenerable; it's 2 MB)
- Anything under `.secrets/` or `vault/`

**Bypassing:** `git commit --no-verify` (use only for vetted false positives; audit first).

---

## House Rules

1. **No new runtime dependencies without a security review.** Every dep is a supply-chain attack vector. The dependency tree is currently: `pydantic + pydantic-core (Rust binary) + httpx + httpcore + h11 + idna + certifi + sniffio + anyio + typer + click + shellingham + rich + markdown-it-py + mdurl + pygments + typing-extensions + annotated-types + annotated-doc + exceptiongroup + tomli (py<3.11)`. Don't add to it without justification.
2. **No `dict[str, Any]` leaks** out of `clinear.client`. Everything that hits a command handler must be a Pydantic model.
3. **No silent failures.** If something can't be done, raise a `ClinearError` subclass with a helpful `hint`.
4. **No print statements** outside `clinear/output.py` and a couple of init-related scripts. All output goes through the formatter.
5. **No `--insecure` flag, ever.** TLS verification is non-negotiable.

---

## When something breaks

1. Re-run `bash scripts/e2e-test.sh -v` (verbose flag prints full output).
2. Linear API errors will be in the error message verbatim — look for `GRAPHQL_VALIDATION_FAILED` (your query is wrong) vs. `AUTHENTICATION_ERROR` (token issue).
3. Pydantic validation errors mean the response shape changed or the model is wrong. Run with `--verbose` to see the raw response.
4. `clinear raw query 'query { ... }'` is your friend — bypass our models, talk directly to Linear's GraphQL.
5. Re-fetch the schema: `curl -X POST https://api.linear.app/graphql -H "Authorization: $LINEAR_TOKEN" -d '<introspection query>'`. Update fragments/models as needed.

---

## Roadmap

- v0.3 (current) — agent skill bundle + `clinear-mcp` MCP server (1 tool + 7 resources + 6 prompts).
- v0.4 — pytest unit tests, hash-pinned `requirements.txt`, `docs/COMMANDS.md`, `clinear completions` for shell completion install
- v0.5 — `clinear initiative`, `clinear document`, `clinear customer` (next-tier domains)
- v0.6 — config-defined views (`--view my-bugs`), aliases
- v1.0 — stable command surface, full integration with the 8 priority domains
