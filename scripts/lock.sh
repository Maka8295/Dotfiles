#!/bin/bash
# Starts hyprlock at the right size for the screen: hyprlock's sizes are physical pixels,
# so on a 4K screen (the laptop) everything in hypr/hyprlock.conf is doubled, the same
# whole-number scaling as the login screen (1x up to 1440p, 2x at 2160p).
# hypridle runs this (Super+L, the waybar lock button, and before every sleep).

CONF="$HOME/.config/hypr/hyprlock.conf"

# An open scratchpad (special workspace) left open across a lock stops taking clicks after
# unlocking. So it's closed first - instantly, with its slide and dim animations switched
# off, so nothing is mid-animation when the lock screen comes up - and reopened after
# unlocking, back in a working state.
special=$(hyprctl monitors -j | python3 -c 'import json,sys
m = next((m for m in json.load(sys.stdin) if m["focused"]), None)
print(m["specialWorkspace"]["name"].removeprefix("special:") if m else "")')

# the animation an inheriting leaf would get from its parent: "speed bezier style"
anim() {
    hyprctl animations | awk -v leaf="$1" '
        $1 == "name:" { inleaf = ($2 == leaf) }
        inleaf && $1 == "speed:" { speed = $2 }
        inleaf && $1 == "bezier:" { bezier = $2 }
        inleaf && $1 == "style:" { style = $2 }
        END { print speed, bezier, style }'
}

if [ -n "$special" ]; then
    read -r ws_speed ws_bezier ws_style < <(anim workspaces)
    read -r fade_speed fade_bezier _ < <(anim fade)
    hyprctl eval 'hl.animation({ leaf = "specialWorkspaceOut", enabled = false }); hl.animation({ leaf = "fadeDim", enabled = false })' >/dev/null
    hyprctl dispatch "hl.dsp.workspace.toggle_special(\"$special\")" >/dev/null
fi

factor=$(hyprctl monitors -j | python3 -c 'import json,sys
ms = json.load(sys.stdin)
m = next((m for m in ms if m["focused"]), ms[0] if ms else None)
print(max(1, m["height"] // 1080) if m else 1)')

if [ "${factor:-1}" -le 1 ]; then
    hyprlock
else
    # scaled copy: multiply every pixel size (sizes, font sizes, positions, borders);
    # dots_size / dots_spacing are ratios of the box, so they stay as they are
    scaled="${XDG_RUNTIME_DIR:-/tmp}/hyprlock-x$factor.conf"
    python3 - "$CONF" "$scaled" "$factor" <<'PY'
import re, sys
src, out, f = sys.argv[1], sys.argv[2], int(sys.argv[3])
keys = ("size", "font_size", "position", "border_size", "outline_thickness")
def scale(m):
    nums = re.sub(r"-?\d+", lambda n: str(int(n.group(0)) * f), m.group(2))
    return m.group(1) + nums
text = open(src).read()
text = re.sub(r"^(\s*(?:%s)\s*=\s*)([-\d,\s]+?)(?=\s*(?:#|$))" % "|".join(keys), scale, text, flags=re.M)
open(out, "w").write(text)
PY
    hyprlock --config "$scaled"
fi

# unlocked: animations back to what they inherit, then reopen the scratchpad normally
if [ -n "$special" ]; then
    hyprctl eval "hl.animation({ leaf = \"specialWorkspaceOut\", enabled = true, speed = ${ws_speed:-6}, bezier = \"${ws_bezier:-default}\", style = \"${ws_style:-slidevert}\" }); hl.animation({ leaf = \"fadeDim\", enabled = true, speed = ${fade_speed:-7}, bezier = \"${fade_bezier:-default}\" })" >/dev/null
    hyprctl dispatch "hl.dsp.workspace.toggle_special(\"$special\")" >/dev/null
fi
