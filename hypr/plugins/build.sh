#!/bin/bash
# Builds Hyprland plugins from hyprwm/hyprland-plugins against the installed Hyprland.
#
# Plugins are compiled C++ tied to one exact Hyprland build, so the .so files are
# NOT kept in the repo — rerun this script on a new machine and after every
# Hyprland update (a mismatched plugin is refused at load time).
#
# Needs: git, g++, make, pkg-config, and Hyprland's headers (included in the Arch/CachyOS
# hyprland package).

set -euo pipefail

PLUGINS=(borders-plus-plus)

REPO_URL="https://github.com/hyprwm/hyprland-plugins.git"
SRC="${XDG_CACHE_HOME:-$HOME/.cache}/hyprland-plugins"
OUT="${XDG_DATA_HOME:-$HOME/.local/share}/hypr/plugins"

# Exact commit of the installed Hyprland (works outside a Hyprland session too)
HL_COMMIT=$(Hyprland --version | grep -oE 'at commit [0-9a-f]{40}' | awk '{print $3}')
HL_VERSION=$(pkg-config --modversion hyprland)
echo "Hyprland $HL_VERSION ($HL_COMMIT)"

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

echo "Done. Run 'hyprctl reload' (or log out and back in) to load them."
