#!/usr/bin/env python3
"""Applies the dungeonOS theme to Signal Desktop.

    sudo python3 patch.py            theme Signal (safe to rerun; also run by the pacman hook)
    sudo python3 patch.py --restore  put Signal's original files back
    python3 patch.py --to DIR        write a themed copy of app.asar into DIR (for testing)

Signal has no theme support, so this edits its app.asar (the archive holding its interface):
every colour in its stylesheets is moved onto the dungeonOS palette, and dungeonOS.css is
added at the end. The untouched original is kept next to it as app.asar.dungeonOS-orig.
Signal ships with asar integrity checking off, so the edited archive loads normally.
Use Signal's dark theme (Settings > Appearance) for the intended look.
"""
import colorsys, hashlib, json, math, os, re, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASAR = "/usr/lib/signal-desktop/resources/app.asar"
ORIG = ASAR + ".dungeonOS-orig"
MARKER = b"/* dungeonOS theme for Signal */"
STYLESHEETS = ["stylesheets/manifest.css", "stylesheets/tailwind.css", "stylesheets/manifest_bridge.css", "stylesheets/quill.css"]
LAST_LOADED = "stylesheets/tailwind.css"   # background.html loads it last, so extras go at its end

# --------------------------------------------------------------------------- palette

def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))

# greys: Signal's brightness (0-1) -> dungeonOS dark-to-cream ramp
GREY_RAMP = [(0.00, "#0E0C0A"), (0.07, "#141210"), (0.11, "#1A1816"), (0.17, "#24201C"),
             (0.27, "#463D34"), (0.42, "#6F675E"), (0.62, "#9D8E7C"), (0.82, "#C8B8A0"), (1.00, "#EDE2CC")]
GREY_RAMP = [(p, hex_rgb(c)) for p, c in GREY_RAMP]
# accents by hue: colour each hue family takes on (its hue and saturation; brightness is kept)
ACCENTS = [((180, 300), "#7A5E47"),   # Signal blue/purple -> clay (sent bubbles, buttons, links)
           ((80, 180), "#6E7F5A"),    # greens -> moss
           ((40, 80), "#A88A5B"),     # yellows -> brass
           ((0, 40), "#7B4A3E"),      # reds/oranges -> rust
           ((300, 360), "#7B4A3E")]


def lum(r, g, b):
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def map_rgb(r, g, b):
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.18 or l < 0.04 or l > 0.97:
        y = lum(r, g, b)                              # brightness (on the 0-1 sRGB values)
        for (p0, c0), (p1, c1) in zip(GREY_RAMP, GREY_RAMP[1:]):
            if y <= p1:
                t = 0 if p1 == p0 else (y - p0) / (p1 - p0)
                return tuple(a + (b2 - a) * t for a, b2 in zip(c0, c1))
        return GREY_RAMP[-1][1]
    hue = h * 360
    target = next(c for (lo, hi), c in ACCENTS if lo <= hue < hi)
    th, tl, ts = colorsys.rgb_to_hls(*hex_rgb(target))
    # 75% of the original lightness: cream text stays readable on buttons and sent
    # bubbles, while light accents (links) still stand out on the dark background
    return colorsys.hls_to_rgb(th, l * 0.75, min(ts * 1.1, 0.6))


def fmt(r, g, b, a=1.0):
    r, g, b = (max(0, min(255, round(v * 255))) for v in (r, g, b))
    if a >= 0.999:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r},{g},{b},{round(a, 3)})"


# --------------------------------------------------------------------------- css colours

def num(tok, scale=1.0):
    tok = tok.strip()
    if tok == "none":
        return 0.0
    if tok.endswith("%"):
        return float(tok[:-1]) / 100 * scale
    return float(tok)


def args(inner):
    inner = inner.replace(",", " ")
    if "/" in inner:
        main, alpha = inner.split("/", 1)
        return main.split(), alpha.strip()
    parts = inner.split()
    return (parts[:3], parts[3]) if len(parts) == 4 else (parts, None)


def alpha_of(tok):
    if tok is None:
        return 1.0
    return num(tok) if not tok.endswith("%") else float(tok[:-1]) / 100


def oklab_to_rgb(L, a, b):
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    def gamma(x):
        x = max(0.0, min(1.0, x))
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return tuple(gamma(x) for x in lin)


HEX = re.compile(r"(?<![\w-])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b")
FUNC = re.compile(r"\b(rgba?|hsla?|oklab)\(([^()]*)\)")


def recolour_hex(m):
    h = m.group(1)
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return fmt(*map_rgb(r, g, b), a)


def recolour_func(m):
    kind, inner = m.group(1), m.group(2)
    if "var(" in inner or "calc(" in inner or "from" in inner:
        return m.group(0)
    try:
        main, alpha = args(inner)
        if kind.startswith("rgb"):
            r, g, b = (num(t, 255) / 255 for t in main[:3])
        elif kind.startswith("hsl"):
            hh = float(main[0].replace("deg", "")) / 360 % 1
            r, g, b = colorsys.hls_to_rgb(hh, num(main[2], 1), num(main[1], 1))
        else:  # oklab
            r, g, b = oklab_to_rgb(num(main[0], 1), num(main[1]), num(main[2]))
        return fmt(*map_rgb(r, g, b), alpha_of(alpha))
    except (ValueError, IndexError):
        return m.group(0)


def recolour_css(text):
    # selectors like "#root" never look like colours here, but only touch declaration values
    def in_values(block):
        return HEX.sub(recolour_hex, FUNC.sub(recolour_func, block.group(0)))
    return re.sub(r":[^;{}]*", in_values, text)


# --------------------------------------------------------------------------- asar io

def read_asar(path):
    with open(path, "rb") as f:
        raw = f.read()
    pickle_size = struct.unpack_from("<I", raw, 4)[0]
    json_size = struct.unpack_from("<I", raw, 12)[0]
    header = json.loads(raw[16:16 + json_size])
    return header, raw, 8 + pickle_size


def files_in(node, path=""):
    for name, sub in node.get("files", {}).items():
        p = f"{path}/{name}".lstrip("/")
        if "files" in sub:
            yield from files_in(sub, p)
        else:
            yield p, sub


def integrity(data, block=4 * 1024 * 1024):
    return {"algorithm": "SHA256", "hash": hashlib.sha256(data).hexdigest(), "blockSize": block,
            "blocks": [hashlib.sha256(data[i:i + block]).hexdigest() for i in range(0, max(len(data), 1), block)]}


def write_asar(header, raw, data_start, replacements, out):
    """Rebuilds the archive with some files replaced; everything else is copied as-is."""
    entries = sorted(((p, n) for p, n in files_in(header) if "offset" in n and not n.get("unpacked")),
                     key=lambda pn: int(pn[1]["offset"]))
    blobs, offset = [], 0
    for path, node in entries:
        old = int(node["offset"])
        data = replacements.get(path, raw[data_start + old:data_start + old + node["size"]])
        if path in replacements:
            node["size"] = len(data)
            if "integrity" in node:
                node["integrity"] = integrity(data)
        node["offset"] = str(offset)
        offset += len(data)
        blobs.append(data)
    hjson = json.dumps(header, separators=(",", ":")).encode()
    padded = len(hjson) + (4 - len(hjson) % 4) % 4
    head = struct.pack("<IIII", 4, padded + 8, padded + 4, len(hjson)) + hjson + b"\0" * (padded - len(hjson))
    tmp = out + ".tmp"
    with open(tmp, "wb") as f:
        f.write(head)
        for b in blobs:
            f.write(b)
    os.chmod(tmp, 0o644)
    os.replace(tmp, out)


def get(header, raw, data_start, path):
    node = header
    for part in path.split("/"):
        node = node["files"][part]
    o = int(node["offset"])
    return raw[data_start + o:data_start + o + node["size"]]


def theme(source, out):
    header, raw, start = read_asar(source)
    extra = open(os.path.join(HERE, "dungeonOS.css"), "rb").read()
    repl = {}
    for path in STYLESHEETS:
        try:
            css = get(header, raw, start, path).decode()
        except KeyError:
            continue
        css = recolour_css(css).encode()
        if path == LAST_LOADED:
            css += b"\n" + MARKER + b"\n" + extra
        repl[path] = css
    write_asar(header, raw, start, repl, out)
    return sorted(repl)


def main():
    if "--to" in sys.argv:
        out = os.path.join(sys.argv[sys.argv.index("--to") + 1], "app.asar")
        print("themed:", ", ".join(theme(ORIG if os.path.exists(ORIG) else ASAR, out)), "->", out)
        return
    if os.geteuid() != 0:
        sys.exit("run with sudo (it edits Signal's files)")
    if "--restore" in sys.argv:
        if os.path.exists(ORIG):
            shutil.copy2(ORIG, ASAR)
            os.remove(ORIG)
            print("Signal restored to its original look")
        else:
            print("nothing to restore")
        return
    current = open(ASAR, "rb").read()
    if MARKER not in current:
        shutil.copy2(ASAR, ORIG)          # a fresh (or freshly updated) Signal: keep it as the original
    print("themed:", ", ".join(theme(ORIG, ASAR)))
    print("Restart Signal to see it.")


if __name__ == "__main__":
    main()
