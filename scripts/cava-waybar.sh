#!/bin/bash
# Small cava visualiser for waybar (custom/cava). cava writes one line of bar heights
# (0-7, config in cava/waybar/config) per frame; each height becomes a block character
# coloured by how tall it is: moss at the bottom, through sage and brass, to rust at the top.
# Silence draws a flat row in the comment colour.

# When waybar stops this module (or quits), take this script's own cava and awk with it.
# cava doesn't exit when nothing reads its output any more, and killing every cava by name
# would also kill the other bar's while the layouts are swapped.
trap 'trap - TERM INT EXIT; pkill -P $$' TERM INT EXIT
BAR=$PPID

cava -p "$HOME/Dotfiles/cava/waybar/config" | awk -F';' '
BEGIN {
    split("▁ ▂ ▃ ▄ ▅ ▆ ▇ █", ch, " ")
    split("#6E7F5A #6E7F5A #879376 #879376 #A88A5B #A88A5B #7A5E47 #7B4A3E", col, " ")
}
{
    out = ""; total = 0
    for (i = 1; i < NF || (i == NF && $i != ""); i++) {
        h = $i + 0; total += h
        out = out "<span color=\"" col[h + 1] "\">" ch[h + 1] "</span>"
    }
    if (total == 0) out = "<span color=\"#6F675E\">▁▁▁▁▁▁</span>"
    if (out != last) { print out; fflush(); last = out }
}' &

# waybar can quit without stopping its modules, so also stop once it's gone
while kill -0 "$BAR" 2>/dev/null && kill -0 $! 2>/dev/null; do
    sleep 2
done
