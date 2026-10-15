#!/bin/bash
# Starts hyprlock at the right size for the screen: hyprlock's sizes are physical pixels,
# so on a 4K screen (the laptop) everything in hypr/hyprlock.conf is doubled, the same
# whole-number scaling as the login screen (1x up to 1440p, 2x at 2160p).
# hypridle runs this (Super+L, the waybar lock button, and before every sleep).

CONF="$HOME/.config/hypr/hyprlock.conf"

factor=$(hyprctl monitors -j | python3 -c 'import json,sys
ms = json.load(sys.stdin)
m = next((m for m in ms if m["focused"]), ms[0] if ms else None)
print(max(1, m["height"] // 1080) if m else 1)')

if [ "${factor:-1}" -le 1 ]; then
    exec hyprlock
fi

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
exec hyprlock --config "$scaled"
