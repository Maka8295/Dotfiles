#!/bin/bash
# Switches between the vertical (left, default) and horizontal (top) waybar, and turns the
# workspace switching animation to match. The choice is remembered across reboots.

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/waybar-layout"
mkdir -p "$(dirname "$STATE")"

if [ "$(cat "$STATE" 2>/dev/null)" = "horizontal" ]; then
    echo vertical > "$STATE"
else
    echo horizontal > "$STATE"
fi

"$HOME/Dotfiles/scripts/waybar.sh"
echo "waybar layout: $(cat "$STATE")"
