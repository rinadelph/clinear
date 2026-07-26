#!/usr/bin/env bash
# Install the Cliniar agent skill into Swarm OS and/or Claude skill directories.
#
# Usage:
#   bash skills/install.sh [--swarm-only|--claude-only] [--copy]
#   bash skills/install.sh --legacy-links   # also add deprecated clinear links
#   bash skills/install.sh --uninstall [--legacy-links]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/cliniar"
MODE="symlink"
ACTION="install"
TARGETS=("swarm" "claude")
LEGACY_LINKS=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --swarm-only) TARGETS=("swarm") ;;
        --claude-only) TARGETS=("claude") ;;
        --copy) MODE="copy" ;;
        --legacy-links) LEGACY_LINKS=1 ;;
        --uninstall) ACTION="uninstall" ;;
        -h|--help)
            sed -n '2,/^set -e/p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
    shift
done

skill_root() {
    case "$1" in
        swarm) printf '%s\n' "$HOME/.swarmos/skills" ;;
        claude) printf '%s\n' "$HOME/.claude/skills" ;;
    esac
}

remove_managed_link() {
    local path="$1"
    local expected="$2"
    if [ -L "$path" ]; then
        if [ "$(readlink "$path")" = "$expected" ]; then
            rm -- "$path"
        else
            echo "  refusing to remove unmanaged symlink: $path" >&2
            return 1
        fi
    elif [ -e "$path" ]; then
        echo "  refusing to remove unmanaged path: $path" >&2
        return 1
    fi
}

install_one() {
    local root canonical legacy
    root="$(skill_root "$1")"
    canonical="$root/cliniar"
    legacy="$root/clinear"
    mkdir -p "$root"

    remove_managed_link "$canonical" "$SRC"
    if [ "$MODE" = "copy" ]; then
        if [ -e "$canonical" ]; then
            echo "  refusing to overwrite unmanaged path: $canonical" >&2
            return 1
        fi
        cp -R "$SRC" "$canonical"
        echo "  installed copy: $canonical"
    else
        ln -s "$SRC" "$canonical"
        echo "  installed symlink: $canonical"
    fi

    if [ "$LEGACY_LINKS" -eq 1 ]; then
        if ! remove_managed_link "$legacy" "$canonical"; then
            echo "  keeping unmanaged legacy path: $legacy" >&2
            return 0
        fi
        ln -s "$canonical" "$legacy"
        echo "  installed deprecated compatibility symlink: $legacy"
    fi
}

uninstall_one() {
    local root canonical legacy
    root="$(skill_root "$1")"
    canonical="$root/cliniar"
    legacy="$root/clinear"
    remove_managed_link "$canonical" "$SRC" || true
    if [ "$LEGACY_LINKS" -eq 1 ]; then
        remove_managed_link "$legacy" "$canonical" || true
    fi
}

if [ ! -d "$SRC" ]; then
    echo "ERROR: source directory not found: $SRC" >&2
    exit 1
fi

if [ "$ACTION" = "install" ]; then
    echo "Installing Cliniar skill (mode: $MODE)"
    for target in "${TARGETS[@]}"; do install_one "$target"; done
else
    echo "Uninstalling managed Cliniar skill paths"
    for target in "${TARGETS[@]}"; do uninstall_one "$target"; done
fi
