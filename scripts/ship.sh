#!/usr/bin/env bash
# Ship clinear v0.2.0: init git, install hook, commit, push, tag, release, publish to PyPI.
# Token reads from env only — never written to disk.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "==> Working dir: $ROOT"

# 1. Final secret scan before anything touches git
echo "==> [1/9] Final secret audit"
# Build patterns dynamically so this script doesn't trip its own scanner
P1="lin"; P1="${P1}_api_[A-Za-z0-9]{20,}"
P2="pypi"; P2="${P2}-Ag[A-Za-z0-9_-]{20,}"
LEAKS=$(grep -rIn --exclude-dir=.venv --exclude-dir=.git --exclude-dir=schema --exclude-dir=dist --exclude=ship.sh \
    -E "${P1}|${P2}" \
    . 2>/dev/null | grep -vE 'lin_api_\.\.\.|lin_api_…|lin_api_\\.\.\.|lin_api_XXX' || true)
if [ -n "$LEAKS" ]; then
    echo "ABORT: Leaked credentials detected:" >&2
    echo "$LEAKS" >&2
    exit 9
fi
echo "    OK — no leaked credentials in source."

# 2. Init git if not present
echo "==> [2/9] Git init"
if [ ! -d .git ]; then
    git init -q -b main
    git config user.name  "Luis Alejandro Rincon"
    git config user.email "rnadales@cloverve.com"
fi

# 3. Install pre-commit hook
echo "==> [3/9] Install pre-commit hook"
bash scripts/install-hooks.sh

# 4. Stage and verify what we're about to commit
echo "==> [4/9] Staging files"
git add -A
echo "    Files staged:"
git diff --cached --name-only | sed 's/^/      /'

# 5. Run the pre-commit hook manually as a final gate
echo "==> [5/9] Running pre-commit hook against staged files"
.git/hooks/pre-commit

# 6. Initial commit
echo "==> [6/9] Commit"
git commit -m "release: v0.2.0

Initial public release of clinear — a type-safe Linear CLI built on
Pydantic v2 + httpx + Typer.

Features:
- 10 command groups: me, auth, init, team, issue, project, cycle,
  comment, label, raw
- 6 output formats: human, json, yaml, md, plain, ids
- Async GraphQL client with rate-limit awareness
- Pre-commit hook blocking secrets and forbidden file types
- 36/36 E2E tests passing against the live Linear API"

# 7. Create GitHub repo + push
echo "==> [7/9] Create GitHub repo and push"
if ! gh repo view rinadelph/clinear >/dev/null 2>&1; then
    gh repo create rinadelph/clinear \
        --public \
        --source . \
        --description "Type-safe Linear CLI built on Pydantic v2 + httpx + Typer. Designed for humans, agents, and CI/CD pipelines." \
        --homepage "https://pypi.org/project/clinear/" \
        --push
else
    git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/rinadelph/clinear.git"
    git push -u origin main
fi

# 8. Tag and release
echo "==> [8/9] Tag v0.2.0 and create GitHub release"
git tag -a v0.2.0 -m "v0.2.0 — initial public release"
git push origin v0.2.0

# Build before release so we attach the artifacts
rm -rf dist build
uv build
ls -la dist/

# Extract the 0.2.0 section of CHANGELOG for release notes
awk '/^## \[0\.2\.0\]/{flag=1; next} /^## \[/{flag=0} flag' CHANGELOG.md > /tmp/clinear-release-notes.md

gh release create v0.2.0 \
    --title "v0.2.0 — Initial public release" \
    --notes-file /tmp/clinear-release-notes.md \
    dist/clinear-0.2.0-py3-none-any.whl \
    dist/clinear-0.2.0.tar.gz
rm -f /tmp/clinear-release-notes.md

# 9. Publish to PyPI
echo "==> [9/9] Publishing to PyPI"
if [ -z "${UV_PUBLISH_TOKEN:-}" ]; then
    echo "ABORT: UV_PUBLISH_TOKEN not in environment. Set it before running this script." >&2
    exit 3
fi
uv publish

echo ""
echo "================================================================"
echo "  clinear v0.2.0 SHIPPED"
echo "================================================================"
echo "  GitHub: https://github.com/rinadelph/clinear"
echo "  PyPI:   https://pypi.org/project/clinear/0.2.0/"
echo "  Tag:    v0.2.0"
echo ""
echo "Test from PyPI:"
echo "  uv tool install --refresh clinear"
echo "  clinear --version"
echo "================================================================"
