#!/usr/bin/env bash
# Build and publish a Cliniar release from an already-versioned, clean checkout.
# This script does not create repositories, commits, or deployment-specific
# configuration. Set CLINIAR_RELEASE_REPOSITORY only to override the current
# GitHub remote. Set CLINIAR_CHECK_LEGACY_ARTIFACTS=1 for the one-release alias
# compatibility check.
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="$(tr -d '[:space:]' < VERSION)"
TAG="v$VERSION"
NOTES_FILE="$(mktemp "${TMPDIR:-/tmp}/cliniar-release-notes.XXXXXX.md")"
trap 'rm -f "$NOTES_FILE"' EXIT

if [ -n "$(git status --porcelain)" ]; then
    echo "ABORT: release checkout is not clean" >&2
    exit 2
fi

echo "==> Auditing source for credentials"
P1="lin"; P1="${P1}_api_[A-Za-z0-9]{20,}"
P2="pypi"; P2="${P2}-Ag[A-Za-z0-9_-]{20,}"
LEAKS="$(grep -rIn --exclude-dir=.venv --exclude-dir=.git \
    --exclude-dir=schema --exclude-dir=dist --exclude=ship.sh \
    -E "${P1}|${P2}" . 2>/dev/null |
    grep -vE 'lin_api_\.\.\.|lin_api_…|lin_api_\\.\.\.|lin_api_XXX' || true)"
if [ -n "$LEAKS" ]; then
    printf 'ABORT: leaked credentials detected:\n%s\n' "$LEAKS" >&2
    exit 9
fi

echo "==> Running release gate"
bash scripts/pre-commit.sh

echo "==> Building Cliniar $VERSION"
rm -rf dist build
uv build
WHEEL="dist/cliniar-${VERSION}-py3-none-any.whl"
SDIST="dist/cliniar-${VERSION}.tar.gz"
test -f "$WHEEL"
test -f "$SDIST"

if [ "${CLINIAR_CHECK_LEGACY_ARTIFACTS:-0}" = "1" ]; then
    echo "==> Checking deprecated clinear aliases in canonical wheel"
    unzip -p "$WHEEL" "cliniar-${VERSION}.dist-info/entry_points.txt" |
        grep -Eq '^clinear(-mcp|-serve)?[[:space:]]*='
fi

awk -v version="$VERSION" '
    $0 ~ "^## \\[" version "\\]" { found=1; next }
    found && /^## \[/ { exit }
    found { print }
' CHANGELOG.md > "$NOTES_FILE"
test -s "$NOTES_FILE"

echo "==> Creating GitHub release $TAG"
REPOSITORY_ARGS=()
if [ -n "${CLINIAR_RELEASE_REPOSITORY:-}" ]; then
    REPOSITORY_ARGS=(--repo "$CLINIAR_RELEASE_REPOSITORY")
fi
gh release create "$TAG" "${REPOSITORY_ARGS[@]}" \
    --title "Cliniar $VERSION" \
    --notes-file "$NOTES_FILE" \
    "$WHEEL" "$SDIST"

if [ -z "${UV_PUBLISH_TOKEN:-}" ]; then
    echo "ABORT: UV_PUBLISH_TOKEN is not set" >&2
    exit 3
fi
uv publish "$WHEEL" "$SDIST"

echo "Cliniar $VERSION published. Verify with:"
echo "  uv tool install --refresh cliniar"
echo "  cliniar --version"
