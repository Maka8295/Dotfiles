#!/bin/bash
# Switches waybar between the horizontal (top) and vertical (left) layouts.
# The choice is remembered, so waybar starts in the same layout after a reboot.

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/waybar-layout"
mkdir -p "$(dirname "$STATE")"

if [ "$(cat "$STATE" 2>/dev/null)" = "vertical" ]; then
    echo horizontal > "$STATE"
else
    echo vertical > "$STATE"
fi

"$HOME/Dotfiles/scripts/waybar.sh"
echo "waybar layout: $(cat "$STATE")"
