#!/usr/bin/env python3
"""Builds the dungeonOS KiCad colour theme: 10.0/colors/dungeonOS.json, and selects it in
every KiCad program (schematic, PCB, footprint/symbol editors, 3D viewer, Gerber viewer).

    python3 ~/Dotfiles/kicad/make-theme.py

Main colours are picked by hand below; anything else KiCad has a colour for is moved onto
the dungeonOS palette automatically (same mapping as ../signal/patch.py). KiCad must be
closed while this runs, or it will overwrite the theme selection when it quits.
"""
import glob, json, os, re, sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "signal"))
from patch import map_rgb   # noqa: E402

CONF = os.path.join(HERE, "10.0")
OUT = os.path.join(CONF, "colors", "dungeonOS.json")

# palette
BG, BG_DARK, SURFACE, BAND, BORDER = "#1A1816", "#141210", "#24201C", "#463D34", "#7E705D"
FG, FG_MUTED, COMMENT, CREAM = "#C8B8A0", "#9D8E7C", "#6F675E", "#DDD0BD"
MOSS, SAGE, BRASS, CLAY, STEEL, RUST = "#6E7F5A", "#879376", "#A88A5B", "#7A5E47", "#8F8B81", "#7B4A3E"
BRASS_LIGHT, CLAY_LIGHT, RUST_LIGHT, RUST_BRIGHT, TEAL = "#B79B6B", "#B99A80", "#985747", "#B5604B", "#6A8A7A"
INNER = [BRASS, SAGE, STEEL, CLAY_LIGHT, MOSS, RUST_LIGHT, BRASS_LIGHT, FG_MUTED, CLAY, "#7A8A7C"]

SCHEMATIC = {
    "background": BG, "grid": BAND, "grid_axes": COMMENT, "cursor": FG, "page_limits": BORDER,
    "worksheet": BORDER, "wire": MOSS, "bus": STEEL, "junction": SAGE, "bus_junction": STEEL,
    "no_connect": CLAY_LIGHT, "component_outline": BRASS, "component_body": SURFACE,
    "pin": BRASS, "pin_name": FG_MUTED, "pin_number": SAGE, "reference": BRASS_LIGHT,
    "value": SAGE, "fields": FG_MUTED, "label_local": FG, "label_global": BRASS,
    "label_hier": CLAY_LIGHT, "net_name": FG_MUTED, "netclass_flag": FG_MUTED,
    "sheet": BORDER, "sheet_background": (SURFACE, 1.0), "sheet_name": BRASS,
    "sheet_filename": FG_MUTED, "sheet_fields": FG_MUTED, "sheet_label": CLAY_LIGHT,
    "note": FG_MUTED, "private_note": STEEL, "note_background": (BG, 0.0), "hidden": COMMENT,
    "erc_error": RUST_BRIGHT, "erc_warning": BRASS_LIGHT, "erc_exclusion": COMMENT,
    "brightened": CREAM, "hovered": SAGE, "shadow": (BRASS, 0.5), "aux_items": FG_MUTED,
    "anchor": RUST_LIGHT, "dnp_marker": RUST_LIGHT, "drag_net_collision": RUST_BRIGHT,
    "op_currents": STEEL, "op_voltages": SAGE, "excluded_from_sim": COMMENT, "rule_area": CLAY,
}
BOARD = {
    "background": BG_DARK, "grid": BAND, "grid_axes": COMMENT, "cursor": FG, "page_limits": BORDER,
    "worksheet": BORDER, "edge_cuts": CREAM, "margin": FG,
    "copper.f": RUST_BRIGHT, "copper.b": TEAL,
    "f_silks": CREAM, "b_silks": FG_MUTED, "f_mask": (MOSS, 0.4), "b_mask": (CLAY, 0.4),
    "f_paste": (FG, 0.6), "b_paste": (FG_MUTED, 0.6), "f_fab": STEEL, "b_fab": COMMENT,
    "f_crtyd": CLAY_LIGHT, "b_crtyd": CLAY, "f_adhes": SAGE, "b_adhes": MOSS,
    "dwgs_user": FG_MUTED, "cmts_user": STEEL, "eco1_user": SAGE, "eco2_user": BRASS,
    "via_through": FG, "via_blind_buried": CLAY_LIGHT, "via_micro": SAGE,
    "via_hole": "#2A2520", "via_hole_walls": BRASS, "plated_hole": BRASS, "pad_plated_hole": BRASS,
    "pad_through_hole": FG, "pad_front": RUST_BRIGHT, "pad_back": TEAL,
    "ratsnest": (FG, 0.6), "drc_error": (RUST_BRIGHT, 0.8), "drc_warning": (BRASS_LIGHT, 0.8),
    "drc_exclusion": COMMENT, "anchor": RUST_LIGHT, "aux_items": FG, "points": BRASS,
    "locked_shadow": (BRASS, 0.5), "conflicts_shadow": (RUST, 0.5), "outline_area": STEEL,
    "footprint_text_front": CREAM, "footprint_text_back": FG_MUTED, "footprint_text_invisible": COMMENT,
    "no_connect": CLAY_LIGHT, "pad_net_names": CREAM, "track_net_names": CREAM, "via_net_names": BG_DARK,
}
BOARD.update({f"copper.in{i}": INNER[(i - 1) % len(INNER)] for i in range(1, 31)})
BOARD.update({f"user_{i}": INNER[(i + 2) % len(INNER)] for i in range(1, 46)})
# PCB editor only: see-through copper so the other layers show, and no shading over the board area
PCB = {**BOARD, **{k: (v, 0.75) for k, v in BOARD.items() if k.startswith("copper.")},
       "outline_area": (STEEL, 0.0)}
VIEWER_3D = {
    "background_top": "#2A2520", "background_bottom": BG_DARK, "board": (CLAY, 0.9),
    "copper": "#B99A6B", "silkscreen_top": CREAM, "silkscreen_bottom": CREAM,
    "soldermask_top": (BAND, 0.85), "soldermask_bottom": (BAND, 0.85), "solderpaste": FG_MUTED,
}
GERBVIEW = {"background": BG_DARK, "grid": BAND, "axes": COMMENT, "dcodes": FG,
            "negative_objects": RUST, "page_limits": BORDER, "worksheet": BORDER}


def hex_to_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def kicad_colour(value, alpha=None):
    r, g, b = hex_to_rgb(value)
    if alpha is None or alpha >= 1:
        return f"rgb({r}, {g}, {b})"
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def pick(choice):
    return kicad_colour(*choice) if isinstance(choice, tuple) else kicad_colour(choice)


def fallback(value):
    """Any colour we didn't pick by hand: move it onto the palette, keeping its alpha."""
    m = re.match(r"rgba?\(([^)]*)\)", value)
    nums = [float(x) for x in m.group(1).split(",")]
    r, g, b = map_rgb(*(v / 255 for v in nums[:3]))
    a = nums[3] if len(nums) == 4 else None
    return kicad_colour("#%02x%02x%02x" % tuple(round(v * 255) for v in (r, g, b)), a)


def build(section, template, chosen, prefix=""):
    out = {}
    for key, value in template.items():
        path = prefix + key
        if isinstance(value, dict):
            out[key] = build(section, value, chosen, path + ".")
        elif isinstance(value, str) and value.startswith("rgb"):
            out[key] = pick(chosen[path]) if path in chosen else fallback(value)
        else:
            out[key] = value                      # booleans etc. stay as they are
    return out


def main():
    # structure: any existing theme in the colors folders (the installed third-party
    # theme, or a previous dungeonOS.json) - every KiCad 10 theme has the same keys
    candidates = glob.glob(os.path.expanduser("~/.local/share/kicad/10.0/3rdparty/colors/*/*.json")) + [OUT]
    existing = [p for p in candidates if os.path.exists(p)]
    template_path = max(existing, key=lambda p: len(json.load(open(p))))
    template = json.load(open(template_path))

    # use the template with the most sections (some themes skip e.g. the footprint editor)
    sections = {"3d_viewer": VIEWER_3D, "board": PCB, "fpedit": BOARD, "schematic": SCHEMATIC}
    theme = {name: build(name, template[name], chosen) for name, chosen in sections.items() if name in template}
    if "gerbview" in template:
        g = template["gerbview"]
        theme["gerbview"] = {**build("gerb", {k: v for k, v in g.items() if k != "layers"}, GERBVIEW),
                             "layers": [kicad_colour(INNER[i % len(INNER)]) for i in range(len(g.get("layers", [])))]}
    theme["meta"] = {"filename": "dungeonOS", "name": "dungeonOS", "version": template["meta"].get("version", 5)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(theme, f, indent=2)
    print(f"wrote {OUT} (structure from {os.path.basename(template_path)})")

    # select it in every KiCad program
    for path in sorted(glob.glob(os.path.join(CONF, "*.json"))):
        if path.endswith(("installed_packages.json",)):
            continue
        settings = json.load(open(path))
        appearance = settings.get("appearance")
        if isinstance(appearance, dict) and "color_theme" in appearance:
            appearance["color_theme"] = "dungeonOS"
            with open(path, "w") as f:
                json.dump(settings, f, indent=2)
            print(f"  {os.path.basename(path)}: color_theme -> dungeonOS")


if __name__ == "__main__":
    main()
