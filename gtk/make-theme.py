#!/usr/bin/env python3
"""Builds the dungeonOS GTK3 theme (Nemo, file dialogs, pavucontrol, ...).

    python3 ~/Dotfiles/gtk/make-theme.py

Takes GTK3's own dark Adwaita stylesheet out of libgtk and moves every colour onto the
dungeonOS palette (the same mapping as the Signal theme), writing ./dungeonOS/. Rerun it
after a GTK update to pick up Adwaita's changes.
"""
import os, re, subprocess, sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "signal"))
from patch import recolour_css, recolour_hex, recolour_func, HEX, FUNC   # noqa: E402

LIB = "/usr/lib/libgtk-3.so.0"
SRC = "/org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css"
OUT = os.path.join(HERE, "dungeonOS")

css = subprocess.run(["gresource", "extract", LIB, SRC], capture_output=True, check=True).stdout.decode()
# Adwaita's images (checkboxes, radios, ...) live inside libgtk; point at them there
css = re.sub(r'url\("(assets/[^"]+)"\)', r'url("resource:///org/gtk/libgtk/theme/Adwaita/\1")', css)
css = recolour_css(css)
# "@define-color name value;" lines have no ":" so recolour_css skips them; do them too
def define(m):
    value = m.group(2)
    value = {"white": "#ffffff", "black": "#000000"}.get(value.strip(), value)
    return m.group(1) + HEX.sub(recolour_hex, FUNC.sub(recolour_func, value)) + ";"
css = re.sub(r"(@define-color\s+\S+\s+)([^;]+);", define, css)

os.makedirs(os.path.join(OUT, "gtk-3.0"), exist_ok=True)
header = "/* dungeonOS: GTK3's dark Adwaita, recoloured by ~/Dotfiles/gtk/make-theme.py */\n"
for name in ("gtk.css", "gtk-dark.css"):
    with open(os.path.join(OUT, "gtk-3.0", name), "w") as f:
        f.write(header + css)
with open(os.path.join(OUT, "index.theme"), "w") as f:
    f.write("[Desktop Entry]\nType=X-GNOME-Metatheme\nName=dungeonOS\n"
            "Comment=Dark Adwaita in the dungeonOS palette\n\n[X-GNOME-Metatheme]\nGtkTheme=dungeonOS\n")
print(f"wrote {OUT} ({len(css)} bytes of CSS)")
