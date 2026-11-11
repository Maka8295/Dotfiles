#!/bin/bash
# Builds Hyprland plugins from hyprwm/hyprland-plugins against the installed Hyprland.
#
#   build.sh               rebuild every plugin
#   build.sh --if-needed   only those missing or built for a different Hyprland (setup.sh uses this)
#
# Plugins are compiled C++ tied to one exact Hyprland build, so the .so files are
# NOT kept in the repo — rerun this script on a new machine and after every
# Hyprland update (a mismatched plugin is refused at load time, and hyprland.lua then
# shows "unknown config key 'plugin.borders_plus_plus...'" errors).
#
# Needs: git, g++, make, pkg-config, and Hyprland's headers (included in the Arch/CachyOS
# hyprland package).

set -euo pipefail

PLUGINS=(borders-plus-plus)

IF_NEEDED=0
case "${1:-}" in
    --if-needed) IF_NEEDED=1 ;;
    "") ;;
    *) sed -n 4,5p "$0"; exit 1 ;;
esac

REPO_URL="https://github.com/hyprwm/hyprland-plugins.git"
SRC="${XDG_CACHE_HOME:-$HOME/.cache}/hyprland-plugins"
OUT="${XDG_DATA_HOME:-$HOME/.local/share}/hypr/plugins"

# Exact commit of the installed Hyprland (works outside a Hyprland session too)
HL_COMMIT=$(Hyprland --version | grep -oE 'at commit [0-9a-f]{40}' | awk '{print $3}')
HL_VERSION=$(pkg-config --modversion hyprland)
echo "Hyprland $HL_VERSION ($HL_COMMIT)"

# Each .so carries the commit of the Hyprland it was built against (the same one Hyprland checks
# when loading it), so a plugin is current when that commit is in the file.
is_current() {
    [ -n "$HL_COMMIT" ] && grep -qaF "$HL_COMMIT" "$OUT/$1.so" 2>/dev/null
}

# Load the plugins into the running Hyprland. hyprctl reload doesn't do it: it skips a plugin that
# already failed to load in this session (an old build, at login after a Hyprland update).
load_plugins() {
    [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ] || return 0
    # right after an update the session is still running the old Hyprland, which refuses them
    if ! hyprctl version 2>/dev/null | grep -qF "$HL_COMMIT"; then
        echo "The running Hyprland is an older build: log out and back in to load the plugins."
        return 0
    fi
    local loaded
    loaded=$(hyprctl plugin list -j 2>/dev/null || true)
    for plugin in "$@"; do
        if grep -qF "\"name\": \"$plugin\"" <<<"$loaded"; then
            [ "$IF_NEEDED" = 1 ] || echo "  $plugin was already loaded; log out and back in to use the new build"
        elif hyprctl plugin load "$OUT/$plugin.so" >/dev/null; then
            echo "  loaded $plugin into the running Hyprland"
        else
            echo "  loading $plugin failed; log out and back in"
        fi
    done
}

if [ "$IF_NEEDED" = 1 ]; then
    NEEDED=()
    for plugin in "${PLUGINS[@]}"; do
        if is_current "$plugin"; then
            echo "  ok    $plugin (built for this Hyprland)"
        else
            NEEDED+=("$plugin")
        fi
    done
    if [ ${#NEEDED[@]} -eq 0 ]; then
        load_plugins "${PLUGINS[@]}"
        exit 0
    fi
    PLUGINS=("${NEEDED[@]}")
fi

if [ -d "$SRC/.git" ]; then
    git -C "$SRC" fetch --quiet origin
else
    git clone --quiet "$REPO_URL" "$SRC"
fi

# hyprpm.toml maps each Hyprland commit to the plugin commit that builds against it
PIN=$(git -C "$SRC" show origin/main:hyprpm.toml | grep -F "\"$HL_COMMIT\"" | grep -oE '"[0-9a-f]{40}"' | sed -n 2p | tr -d '"' || true)
if [ -n "$PIN" ]; then
    echo "Using pinned hyprland-plugins commit $PIN"
    git -C "$SRC" checkout --quiet "$PIN"
else
    echo "No pin for this Hyprland build; trying latest hyprland-plugins (may fail to build)"
    git -C "$SRC" checkout --quiet origin/main
fi

mkdir -p "$OUT"
for plugin in "${PLUGINS[@]}"; do
    echo "Building $plugin..."
    make -C "$SRC/$plugin" all >/dev/null
    install -m 755 "$SRC/$plugin/$plugin.so" "$OUT/$plugin.so"
    echo "  -> $OUT/$plugin.so"
done

load_plugins "${PLUGINS[@]}"
echo "Done."
