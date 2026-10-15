#!/bin/bash
# Opens the scratchpad apps (Super+B) one at a time, each after the previous one's window
# has appeared, so the master layout always stacks them the same way:
#   Signal on the right | cmus top-left, btop below it
# Runs as its own process (started from hyprland.lua) because a Hyprland config reload,
# e.g. when a plugin loads at login, wipes any waiting done inside the Lua config.
# Apps that already have a window are skipped, so it's safe to rerun.

# btop needs about 80x24 cells to draw. Its window is a quarter of the screen, so the font
# depends on the screen's size in layout pixels: 16 on the 1440p desktop; 12 on a smaller
# layout like the 4K laptop at scale 2 (= 1920x1080), which is kitty's 20 zoomed out 4 times
logical_height=$(hyprctl monitors -j | python3 -c 'import json,sys
m = next((m for m in json.load(sys.stdin) if m["focused"]), None)
print(int(m["height"] / m["scale"]) if m else 1440)')
if [ "$logical_height" -lt 1300 ]; then btop_font=12; else btop_font=16; fi

apps=(
    "signal|signal-desktop"
    # no bottom padding: cmus always keeps an empty command-line row at the bottom,
    # which already gives it a bottom margin (kitty's padding on top of it left a gap)
    "cmus-term|kitty --class cmus-term -o 'window_padding_width=15 15 0 15' -e cmus"
    "btop-term|kitty --class btop-term -o font_size=$btop_font -e btop"
)

has_window() {
    hyprctl clients -j | python3 -c 'import json,sys; sys.exit(0 if any(c["class"] == sys.argv[1] for c in json.load(sys.stdin)) else 1)' "$1"
}

for entry in "${apps[@]}"; do
    class="${entry%%|*}"
    cmd="${entry#*|}"
    has_window "$class" && continue
    setsid -f bash -c "$cmd" >/dev/null 2>&1 </dev/null
    # wait up to 15s for its window, then carry on regardless
    for _ in $(seq 150); do
        has_window "$class" && break
        sleep 0.1
    done
done
