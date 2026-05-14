#!/usr/bin/env bash
# clinear pre-commit hook: hard-block secrets and forbidden file types.
#
# Refuses to commit if any staged file contains:
#   - Linear API token         (lin_api_...)
#   - PyPI API token           (pypi-...)
#   - AWS access keys          (AKIA...)
#   - GitHub PATs              (ghp_, ghs_, gho_, ghu_, ghr_)
#   - Google service account   ("type": "service_account")
#   - SSH/PGP private keys     (BEGIN ... PRIVATE KEY)
#   - Slack tokens             (xoxa-/xoxb-/xoxp-/xoxr-)
#
# Also blocks staged files:
#   - *.log
#   - *.env / .env.*
#   - schema/linear-schema.json   (2 MB, regenerable)
#   - anything under .secrets/ or vault/
#
# Bypass (use only for vetted false positives):
#   git commit --no-verify

set -u

red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }

# Get list of staged files (added/copied/modified only)
mapfile -t staged < <(git diff --cached --name-only --diff-filter=ACM)

if [ ${#staged[@]} -eq 0 ]; then
    exit 0
fi

errors=0

# ----- 1. File-name based blocks -----
forbidden_paths_regex='(^|/)(\.env(\..*)?|.*\.log|schema/linear-schema\.json|\.secrets/.*|vault/.*)$'
for f in "${staged[@]}"; do
    if [[ "$f" =~ $forbidden_paths_regex ]]; then
        red "BLOCKED FILE TYPE: $f"
        yellow "  This file type is permanently blocked from this repo."
        yellow "  Add it to .gitignore. If you really need it, use --no-verify (audit first)."
        errors=$((errors + 1))
    fi
done

# ----- 2. Content scans (skip binary blobs) -----

# Pattern => human description
declare -A patterns=(
    ['lin_api_[A-Za-z0-9]{20,}']='Linear API token (lin_api_...)'
    ['pypi-[A-Za-z0-9_-]{16,}']='PyPI API token (pypi-...)'
    ['AKIA[0-9A-Z]{16}']='AWS Access Key ID (AKIA...)'
    ['ghp_[A-Za-z0-9]{30,}']='GitHub personal access token (ghp_...)'
    ['ghs_[A-Za-z0-9]{30,}']='GitHub server-to-server token (ghs_...)'
    ['gho_[A-Za-z0-9]{30,}']='GitHub OAuth token (gho_...)'
    ['ghu_[A-Za-z0-9]{30,}']='GitHub user-to-server token (ghu_...)'
    ['ghr_[A-Za-z0-9]{30,}']='GitHub refresh token (ghr_...)'
    ['xox[abpr]-[A-Za-z0-9-]{10,}']='Slack token (xox...)'
    ['"type":[[:space:]]*"service_account"']='Google service account JSON'
    ['-----BEGIN (RSA |OPENSSH |EC |PGP |DSA |ENCRYPTED )?PRIVATE KEY']='Private key block'
)

for f in "${staged[@]}"; do
    [ -f "$f" ] || continue
    # Skip files larger than 1 MB (likely binary / lock files)
    size=$(stat -c%s -- "$f" 2>/dev/null || echo 0)
    if [ "$size" -gt 1048576 ]; then
        continue
    fi
    # Skip obviously-binary files
    if file -b --mime "$f" 2>/dev/null | grep -q 'charset=binary'; then
        continue
    fi
    # Skip the hook itself and its installer — they describe the patterns they block
    case "$f" in
        scripts/pre-commit.sh|scripts/install-hooks.sh|scripts/ship.sh) continue ;;
    esac
    for pat in "${!patterns[@]}"; do
        if matches=$(grep -nP --color=never "$pat" "$f" 2>/dev/null); then
            red "SECRET DETECTED in $f"
            yellow "  Pattern: ${patterns[$pat]}"
            echo "$matches" | head -3 | sed 's/^/    /' >&2
            errors=$((errors + 1))
        fi
    done
done

if [ "$errors" -gt 0 ]; then
    echo "" >&2
    red "Commit refused: $errors issue(s) found."
    yellow "If you have rotated the credentials and the match is a real false positive,"
    yellow "you can bypass with: git commit --no-verify  (audit first!)"
    exit 1
fi

green "pre-commit OK (${#staged[@]} files scanned, no secrets / forbidden paths)"
exit 0
