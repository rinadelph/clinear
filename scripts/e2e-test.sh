#!/usr/bin/env bash
# Comprehensive E2E test for clinear
# Tests every command in both human and JSON output modes.
#
# Requires: $LINEAR_TOKEN in environment. We never hardcode the token here.

set -u
if [ -z "${LINEAR_TOKEN:-}" ]; then
    echo "ERROR: \$LINEAR_TOKEN is not set. Export it before running these tests." >&2
    echo "Get a token at: https://linear.app/settings/api" >&2
    exit 3
fi
CLI=.venv/bin/clinear

PASS=0
FAIL=0
RESULTS=()

run_test() {
    local name="$1"
    local expect_fail="${EXPECT_FAIL:-0}"
    shift
    echo ""
    echo "=================================================="
    echo "TEST: $name"
    echo "CMD: $*"
    echo "=================================================="
    output=$("$@" 2>&1)
    rc=$?
    echo "$output" | head -40
    echo "[EXIT: $rc]"
    if [ "$expect_fail" = "1" ]; then
        # Expected non-zero exit
        if [ $rc -ne 0 ]; then
            PASS=$((PASS+1))
            RESULTS+=("PASS: $name (expected non-zero, got $rc)")
        else
            FAIL=$((FAIL+1))
            RESULTS+=("FAIL: $name (expected non-zero, got 0)")
        fi
    else
        if [ $rc -eq 0 ]; then
            PASS=$((PASS+1))
            RESULTS+=("PASS: $name")
        else
            FAIL=$((FAIL+1))
            RESULTS+=("FAIL: $name (exit=$rc)")
        fi
    fi
}

# --- Identity / Auth ---
run_test "me (human)" $CLI me
run_test "me (json)" $CLI -o json me
run_test "auth status" $CLI auth status

# --- Teams ---
run_test "team list (human)" $CLI team list
run_test "team list (json)" $CLI -o json team list
run_test "team get CLO" $CLI team get CLO
run_test "team states CLO (human)" $CLI team states CLO
run_test "team states CLO (json)" $CLI -o json team states CLO
run_test "team members CLO (human)" $CLI team members CLO

# --- Projects ---
run_test "project list (human)" $CLI project list
run_test "project list (json)" $CLI -o json project list

# --- Cycles ---
# --- Cycles ---
run_test "cycle current CLO (graceful no-cycle)" $CLI cycle current CLO
run_test "cycle current CLO (json graceful)" $CLI -o json cycle current CLO
run_test "cycle list CLO" $CLI cycle list CLO

# --- Comments ---
run_test "comment list CLO-34" $CLI comment list CLO-34 -n 5

# --- Labels ---
run_test "label list" $CLI label list -n 20
run_test "label list --team CLO" $CLI label list --team CLO

# --- Init ---
TMP_CONFIG=$(mktemp -d)/config.toml
run_test "init --path (custom location)" $CLI init --path "$TMP_CONFIG"
EXPECT_FAIL=1 run_test "init duplicate (expect exit 2)" $CLI init --path "$TMP_CONFIG"
run_test "init --force overwrite" $CLI init --path "$TMP_CONFIG" --force
rm -rf "$(dirname "$TMP_CONFIG")"

# --- Issues ---
run_test "issue list --assignee me -n 3 (human)" $CLI issue list --assignee me -n 3
run_test "issue list --assignee me -n 3 (json)" $CLI -o json issue list --assignee me -n 3
run_test "issue list --team CLO --state Todo -n 5" $CLI issue list --team CLO --state Todo -n 5
run_test "issue list -o ids (xargs-friendly)" $CLI -o ids issue list --assignee me -n 3
run_test "issue get CLO-34 (human)" $CLI issue get CLO-34
run_test "issue get CLO-34 (json)" $CLI -o json issue get CLO-34
run_test "issue url CLO-34" $CLI issue url CLO-34
run_test "issue search login" $CLI issue search login -n 3

# --- Dry-run mutations ---
run_test "issue create --dry-run" $CLI --dry-run issue create --team CLO --title "Test from clinear" --priority 3
run_test "issue update --dry-run" $CLI --dry-run issue update CLO-34 --priority 2

# --- Output formats ---
run_test "issue list -o yaml" $CLI -o yaml issue list --assignee me -n 2
run_test "issue list -o md" $CLI -o md issue list --assignee me -n 3
run_test "issue list -o plain" $CLI -o plain issue list --assignee me -n 3

# --- Raw query ---
run_test "raw query" $CLI raw query 'query { viewer { id name email } }'

# --- Error cases (these SHOULD fail with non-zero exit) ---
EXPECT_FAIL=1 run_test "non-existent team (expect error 4)" $CLI team get NONEXISTENT
EXPECT_FAIL=1 run_test "non-existent issue (expect error 4)" $CLI issue get FAKE-9999

echo ""
echo "================================================================"
echo "SUMMARY: $PASS passed, $FAIL failed"
echo "================================================================"
for r in "${RESULTS[@]}"; do echo "  $r"; done
exit $FAIL
