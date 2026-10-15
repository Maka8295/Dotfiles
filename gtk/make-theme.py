#!/usr/bin/env python3
"""Builds the dungeonOS GTK theme: GTK3 (Nemo, file dialogs) and GTK4 (pavucontrol).

    python3 ~/Dotfiles/gtk/make-theme.py

Takes GTK's own dark stylesheets (GTK3 Adwaita, GTK4 Default) out of libgtk and moves every colour onto the
dungeonOS palette (the same mapping as the Signal theme), writing ./dungeonOS/. Rerun it
after a GTK update to pick up Adwaita's changes.
"""
import os, re, subprocess, sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "signal"))
from patch import recolour_css, recolour_hex, recolour_func, HEX, FUNC   # noqa: E402

OUT = os.path.join(HERE, "dungeonOS")

def build(lib, resource, folder):
    css = subprocess.run(["gresource", "extract", lib, resource], capture_output=True, check=True).stdout.decode()
    # the theme's images (checkboxes, radios, ...) live inside libgtk; point at them there
    base = resource.rsplit("/", 1)[0]
    css = re.sub(r'url\("(assets/[^"]+)"\)', rf'url("resource://{base}/\1")', css)
    css = recolour_css(css)
    # "@define-color name value;" lines have no ":" so recolour_css skips them; do them too
    def define(m):
        value = m.group(2)
        value = {"white": "#ffffff", "black": "#000000"}.get(value.strip(), value)
        return m.group(1) + HEX.sub(recolour_hex, FUNC.sub(recolour_func, value)) + ";"
    css = re.sub(r"(@define-color\s+\S+\s+)([^;]+);", define, css)
    os.makedirs(os.path.join(OUT, folder), exist_ok=True)
    header = f"/* dungeonOS: {resource.rsplit('/', 1)[1]} from {os.path.basename(lib)}, recoloured by ~/Dotfiles/gtk/make-theme.py */\n"
    for name in ("gtk.css", "gtk-dark.css"):
        with open(os.path.join(OUT, folder, name), "w") as f:
            f.write(header + css)
    print(f"wrote {folder}/ ({len(css)} bytes of CSS)")


# GTK3 apps (Nemo, file dialogs, ...) and GTK4 apps (pavucontrol, ...)
build("/usr/lib/libgtk-3.so.0", "/org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css", "gtk-3.0")
build("/usr/lib/libgtk-4.so.1", "/org/gtk/libgtk/theme/Default/Default-dark.css", "gtk-4.0")
with open(os.path.join(OUT, "index.theme"), "w") as f:
    f.write("[Desktop Entry]\nType=X-GNOME-Metatheme\nName=dungeonOS\n"
            "Comment=Dark Adwaita in the dungeonOS palette\n\n[X-GNOME-Metatheme]\nGtkTheme=dungeonOS\n")
print(f"wrote {OUT}")
