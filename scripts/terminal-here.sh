#!/bin/bash
# Super+F: a new kitty with fish. When the focused window is yazi, the terminal opens in the
# folder yazi is showing (yazi moves its own process into that folder, so its cwd is it);
# anywhere else it opens in ~ as usual.

dir="$HOME"
pid=$(hyprctl activewindow | awk '/^\s*pid:/ {print $2}')

# yazi runs inside the focused kitty (Super+D is "kitty yazi"); look through its children
if [ -n "$pid" ]; then
    for child in $(pgrep -P "$pid") $(pgrep -P "$(pgrep -d, -P "$pid")" 2>/dev/null); do
        if [ "$(cat /proc/"$child"/comm 2>/dev/null)" = "yazi" ]; then
            dir=$(readlink "/proc/$child/cwd") || dir="$HOME"
            break
        fi
    done
fi

exec kitty --directory "$dir" fish
