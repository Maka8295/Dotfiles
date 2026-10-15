#!/usr/bin/env bash
# Silently power off the PC after a number of minutes (default 45).
# Detaches from the terminal so closing it won't cancel the timer.
# Starting a new timer replaces the old one. Cancel with: ~/Dotfiles/scripts/sleep.sh cancel
# Used by the right-click menu on waybar's power button (waybar/power_menu.xml).

# kill the sleep inside any running timer; its "&& poweroff" then never runs
pkill -f '^/usr/bin/sleep [0-9]+m$'
[ "$1" = "cancel" ] && exit 0

MIN="${1:-45}"
setsid nohup bash -c "/usr/bin/sleep ${MIN}m && systemctl poweroff" >/dev/null 2>&1 < /dev/null &
