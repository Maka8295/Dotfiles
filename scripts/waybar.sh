#!/bin/bash
# Starts (or restarts) waybar in the layout last picked with waybar-toggle.sh.
# Horizontal = waybar/config.jsonc + style.css, vertical = waybar/vertical/.

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/waybar-layout"
DIR="$HOME/Dotfiles/waybar"

pkill -x waybar
while pgrep -x waybar >/dev/null; do sleep 0.1; done

if [ "$(cat "$STATE" 2>/dev/null)" = "vertical" ]; then
    setsid -f waybar -c "$DIR/vertical/config.jsonc" -s "$DIR/vertical/style.css" >/dev/null 2>&1 </dev/null
else
    setsid -f waybar -c "$DIR/config.jsonc" -s "$DIR/style.css" >/dev/null 2>&1 </dev/null
fi
