#!/usr/bin/env bash
# Install the clinear skill into the user's skill directories.
#
# Default behavior: install into BOTH
#   ~/.swarmos/skills/clinear     (for Swarm OS agents)
#   ~/.claude/skills/clinear      (for Claude Code / Claude Desktop)
#
# Flags:
#   --swarm-only      Install only the Swarm OS location
#   --claude-only     Install only the Claude location
#   --copy            Use `cp -r` instead of symlinks (e.g. for read-only systems)
#   --uninstall       Remove the installed skill from both locations
#
# Usage:
#   bash skills/install.sh              # install to both
#   bash skills/install.sh --swarm-only
#   bash skills/install.sh --uninstall

set -euo pipefail

# Resolve the source dir to an absolute path so symlinks work from anywhere.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/clinear"

SWARM_DIR="$HOME/.swarmos/skills/clinear"
CLAUDE_DIR="$HOME/.claude/skills/clinear"

MODE="symlink"
TARGETS=("swarm" "claude")
ACTION="install"

while [ $# -gt 0 ]; do
    case "$1" in
        --swarm-only)  TARGETS=("swarm") ;;
        --claude-only) TARGETS=("claude") ;;
        --copy)        MODE="copy" ;;
        --uninstall)   ACTION="uninstall" ;;
        -h|--help)
            sed -n '2,/^set -e/p' "$0" | sed 's/^# \{0,1\}//' | head -20
            exit 0
            ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
    shift
done

target_path() {
    case "$1" in
        swarm)  echo "$SWARM_DIR" ;;
        claude) echo "$CLAUDE_DIR" ;;
    esac
}

install_one() {
    local target_name="$1"
    local target_path; target_path=$(target_path "$target_name")
    local parent; parent=$(dirname "$target_path")

    mkdir -p "$parent"

    if [ -L "$target_path" ] || [ -d "$target_path" ]; then
        echo "  removing existing $target_path"
        rm -rf "$target_path"
    fi

    if [ "$MODE" = "copy" ]; then
        cp -r "$SRC" "$target_path"
        echo "  installed (copy) → $target_path"
    else
        if ln -s "$SRC" "$target_path" 2>/dev/null; then
            echo "  installed (symlink) → $target_path"
        else
            echo "  symlink failed, falling back to copy"
            cp -r "$SRC" "$target_path"
            echo "  installed (copy) → $target_path"
        fi
    fi
}

uninstall_one() {
    local target_name="$1"
    local target_path; target_path=$(target_path "$target_name")
    if [ -L "$target_path" ] || [ -d "$target_path" ]; then
        rm -rf "$target_path"
        echo "  removed $target_path"
    else
        echo "  not present: $target_path"
    fi
}

if [ ! -d "$SRC" ]; then
    echo "ERROR: source directory not found: $SRC" >&2
    echo "Run this from a checked-out clinear repository." >&2
    exit 1
fi

case "$ACTION" in
    install)
        echo "Installing clinear skill (mode: $MODE)"
        for t in "${TARGETS[@]}"; do install_one "$t"; done
        echo "Done. Verify with: ls -la $HOME/.swarmos/skills/clinear $HOME/.claude/skills/clinear 2>/dev/null || true"
        ;;
    uninstall)
        echo "Uninstalling clinear skill"
        for t in "${TARGETS[@]}"; do uninstall_one "$t"; done
        ;;
esac
