#!/bin/bash
# Starts (or restarts) waybar in the layout last picked with waybar-toggle.sh, and points
# Hyprland's workspace animation the same way. Vertical (left side) is the default.
# Horizontal = waybar/config.jsonc + style.css, vertical = waybar/vertical/.

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/waybar-layout"
DIR="$HOME/Dotfiles/waybar"
LAYOUT=$(cat "$STATE" 2>/dev/null)
[ "$LAYOUT" = "horizontal" ] || LAYOUT=vertical

pkill -x waybar
while pgrep -x waybar >/dev/null; do sleep 0.1; done

if [ "$LAYOUT" = "vertical" ]; then
    setsid -f waybar -c "$DIR/vertical/config.jsonc" -s "$DIR/vertical/style.css" >/dev/null 2>&1 </dev/null
    style=slidevert     # workspaces slide up/down, like the bar's stacked numerals
else
    setsid -f waybar -c "$DIR/config.jsonc" -s "$DIR/style.css" >/dev/null 2>&1 </dev/null
    style=slide         # workspaces slide left/right, like the bar's row of numerals
fi

# hyprland.lua picks the same style when it loads; this applies it right away. The
# scratchpad's close animation is set too, since lock.sh gives it its own setting.
hyprctl eval "hl.animation({ leaf = \"workspaces\", enabled = true, speed = 6, bezier = \"default\", style = \"$style\" }); hl.animation({ leaf = \"specialWorkspaceOut\", enabled = true, speed = 6, bezier = \"default\", style = \"$style\" })" >/dev/null 2>&1
