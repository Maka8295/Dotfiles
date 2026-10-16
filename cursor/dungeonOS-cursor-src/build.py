#!/usr/bin/env python3
"""Builds the dungeonOS-cursor Xcursor theme.

    python3 build.py

Writes ../dungeonOS-cursor/. Sprites in fft/ are cut from Final Fantasy Tactics'
item icon sheet:
  - main pointer:     fft/sword.png            (gold sword with the red jewel)
  - link pointer:     fft/sword-silver.png     (silver sword with the blue jewel)
  - text cursor:      fft/staff.png            (gold staff)
  - crosshair / zoom: fft/shuriken.png         (silver shuriken)
  - loading:          fft/potions/*.png        (animated, cycles through the potions)
  - help:             fft/tome.png             (gold tome)
  - not allowed:      fft/shield.png           (rust-rimmed shield)
  - grab / move:      fft/gauntlet-gold.png    (silver gauntlet while grabbing)
  - link / alias:     fft/chain.png            (silver chain)
  - copy:             fft/quill.png            (green quill)
(art.py's hand-drawn gauntlet is no longer used, but kept in case you want it back.)
Every other cursor (resize arrows and the like) is taken from ../miku-cursor-linux and
recoloured into the dungeonOS palette. The theme is self-contained (no Inherits=):
Hyprland let inherited Miku cursors win over ours when both had the same name.

All art sits on a 32x32 grid like the Miku cursor and is only ever scaled by whole
numbers, so at the 64px size Hyprland uses every art pixel is exactly 2x2 screen pixels.
Needs python-pillow.
"""
import os
import struct
import sys

sys.dont_write_bytecode = True  # keep __pycache__ out of the dotfiles repo
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image  # noqa: E402

import art  # noqa: E402

THEME_NAME = "dungeonOS-cursor"
SOURCE = "miku-cursor-linux"     # sibling theme the remaining cursors are recoloured from
OUT = os.path.join(os.path.dirname(HERE), THEME_NAME)

GRID = 32                     # art grid, same as the Miku cursor
SIZES = (32, 64, 96, 128)     # whole-number multiples of the grid only, so pixels stay sharp;
                              # 128 = size 64 on a scale-2 screen like the 4K laptop
XCURSOR_IMAGE = 0xFFFD0002

# Recolouring: each pixel of a borrowed cursor is matched by brightness to one of these
# (dark outline -> bronze/brass -> pale highlight), so the art keeps its shading but
# stays a crisp, small palette.
RAMP = ["#141210", "#463D34", "#7A5E47", "#A88A5B", "#C8B8A0", "#EDE2CC"]


# ---------------------------------------------------------------------------- art


def grid_from_rows(rows):
    """art.py text rows -> 32x32 RGBA image."""
    im = Image.new("RGBA", (GRID, GRID))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = art.PALETTE[ch]
            if col:
                im.putpixel((x, y), tuple(int(col[i:i + 2], 16) for i in (1, 3, 5)) + (255,))
    return im


def sprites(*paths):
    """Sprite PNGs -> 32x32 grids, all trimmed to the same box (so animation frames
    don't jump around) and placed in the top-left. Returns (grids, box size)."""
    ims = [Image.open(os.path.join(HERE, p)).convert("RGBA") for p in paths]
    boxes = [im.getbbox() for im in ims]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes))
    w, h = box[2] - box[0], box[3] - box[1]
    assert w <= GRID and h <= GRID, "sprite must fit 32x32"
    grids = []
    for im in ims:
        g = Image.new("RGBA", (GRID, GRID))
        g.paste(im.crop(box), (0, 0))
        grids.append(g)
    return grids, (w, h)


def centre(size):
    return (size[0] // 2, size[1] // 2)


def left_of_middle(grid, size):
    """The clear pixel just left of a sprite at its middle row, as a hotspot that stays
    touching the sprite at every size (the right-hand screen pixel of that art pixel)."""
    y = size[1] // 2
    x = next(x for x in range(size[0]) if grid.getpixel((x, y))[3]) - 1
    return lambda scale: ((x + 1) * scale - 1, y * scale + scale // 2)


def sprite(path):
    """One sprite with its hotspot in the middle."""
    grids, size = sprites(path)
    return grids, centre(size)


SWORD, _ = sprites("fft/sword.png")
SILVER_SWORD, _ = sprites("fft/sword-silver.png")
STAFF, STAFF_SIZE = sprites("fft/staff.png")
SHURIKEN, SHURIKEN_SIZE = sprites("fft/shuriken.png")
POTIONS, POTION_SIZE = sprites(*sorted(f"fft/potions/{f}" for f in os.listdir(os.path.join(HERE, "fft/potions"))))
POTION_DELAY_MS = 150
TOME, TOME_HS = sprite("fft/tome.png")
SHIELD, SHIELD_HS = sprite("fft/shield.png")
GAUNTLET_GOLD, GAUNTLET_GOLD_HS = sprite("fft/gauntlet-gold.png")
GAUNTLET_SILVER, GAUNTLET_SILVER_HS = sprite("fft/gauntlet-silver.png")
CHAIN, CHAIN_HS = sprite("fft/chain.png")
QUILL, QUILL_HS = sprite("fft/quill.png")

# cursor file -> (frames, hotspot on the grid, ms per frame, other names that should point at it)
CURSORS = {
    # sword tip is the sprite's top-left corner
    "left_ptr": (SWORD, (0, 0), 0,
                 ["default", "arrow", "top_left_arrow", "left_arrow", "context-menu"]),
    # links/buttons: same sword shape in silver, tip in the same spot
    "pointer": (SILVER_SWORD, (0, 0), 0,
                ["hand", "hand1", "hand2", "pointing_hand",
                 "e29285e634086352946a0e7090d73106", "9d800788f1b08800ae810202380a0822"]),
    # text: click point is the pixel just left of the staff, halfway up, so the text caret
    # lands at the staff's left edge
    "xterm": (STAFF, left_of_middle(STAFF[0], STAFF_SIZE), 0, ["text", "ibeam"]),
    "crosshair": (SHURIKEN, centre(SHURIKEN_SIZE), 0,
                  ["cross", "tcross", "cell", "cross_reverse", "diamond_cross",
                   "zoom-in", "zoom-out", "zoom_in", "zoom_out"]),
    "wait": (POTIONS, centre(POTION_SIZE), POTION_DELAY_MS,
             ["watch", "progress", "left_ptr_watch", "half-busy",
              "08e8e1c95fe2fc01f976f1e063a24ccd", "3ecb610c1bf2410f44200f48c40d3599"]),
    "help": (TOME, TOME_HS, 0,
             ["question_arrow", "whats_this", "left_ptr_help", "dnd_ask", "dnd-ask",
              "5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b"]),
    "not-allowed": (SHIELD, SHIELD_HS, 0,
                    ["forbidden", "crossed_circle", "circle", "no-drop", "dnd-no-drop",
                     "dnd-none", "03b6e0fcb3499374a867c041f52298f0"]),
    "grab": (GAUNTLET_GOLD, GAUNTLET_GOLD_HS, 0,
             ["openhand", "fleur", "move", "all-scroll", "size_all", "dnd-move",
              "4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f"]),
    "grabbing": (GAUNTLET_SILVER, GAUNTLET_SILVER_HS, 0,
                 ["closedhand", "dragging"]),
    "link": (CHAIN, CHAIN_HS, 0,
             ["alias", "dnd-link", "3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ed57b41487f"]),
    "copy": (QUILL, QUILL_HS, 0,
             ["dnd-copy", "1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872"]),
}


# ---------------------------------------------------------------------- xcursor io


def encode(images):
    """images: list of (nominal size, width, height, xhot, yhot, delay, ARGB ints)."""
    ntoc = len(images)
    data = struct.pack("<4sIII", b"Xcur", 16, 0x10000, ntoc)
    chunks = [struct.pack("<9I", 36, XCURSOR_IMAGE, size, 1, w, h, xh, yh, delay) +
              struct.pack(f"<{w * h}I", *px) for size, w, h, xh, yh, delay, px in images]
    pos = 16 + ntoc * 12
    toc = b""
    for (size, *_), chunk in zip(images, chunks):
        toc += struct.pack("<III", XCURSOR_IMAGE, size, pos)
        pos += len(chunk)
    return data + toc + b"".join(chunks)


def decode(path):
    """Reads an Xcursor file back into the same image tuples encode() takes."""
    with open(path, "rb") as f:
        data = f.read()
    magic, header, _version, ntoc = struct.unpack_from("<4sIII", data, 0)
    assert magic == b"Xcur", path
    images = []
    for i in range(ntoc):
        kind, _subtype, pos = struct.unpack_from("<III", data, header + i * 12)
        if kind != XCURSOR_IMAGE:
            continue
        _hsize, _kind, size, _ver, w, h, xh, yh, delay = struct.unpack_from("<9I", data, pos)
        px = list(struct.unpack_from(f"<{w * h}I", data, pos + 36))
        images.append((size, w, h, xh, yh, delay, px))
    return images


def from_grids(frames, hotspot, delay=0):
    """Our 32x32 art, scaled by whole numbers to every size."""
    images = []
    for size in SIZES:
        scale = size // GRID
        hs = hotspot(scale) if callable(hotspot) else (hotspot[0] * scale, hotspot[1] * scale)
        for grid in frames:
            big = grid.resize((size, size), Image.NEAREST)
            flat = big.get_flattened_data() if hasattr(big, "get_flattened_data") else big.getdata()
            # Xcursor wants premultiplied ARGB; the art only has fully solid or clear pixels
            px = [((a << 24) | (r << 16) | (g << 8) | b) if a else 0 for r, g, b, a in flat]
            images.append((size, size, size, hs[0], hs[1], delay, px))
    return images


RAMP_RGB = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in RAMP]


def add_double_of_64(images):
    """Borrowed cursors only come in 32/48/64/96; add a 128 made by exactly doubling the
    64 (pixel art stays sharp), for size 64 on a scale-2 screen."""
    if any(i[0] == 128 for i in images):
        return images
    extra = []
    for size, w, h, xh, yh, delay, px in images:
        if size != 64:
            continue
        big = []
        for row in range(h):
            line = [p for p in px[row * w:(row + 1) * w] for _ in (0, 1)]
            big += line + line
        extra.append((128, w * 2, h * 2, xh * 2, yh * 2, delay, big))
    return images + extra


def recolour(images):
    """Maps every pixel to the RAMP colour matching its brightness, keeping alpha."""
    out = []
    cache = {}
    for size, w, h, xh, yh, delay, px in images:
        new = []
        for p in px:
            a = p >> 24
            if a == 0:
                new.append(0)
                continue
            if p not in cache:
                # un-premultiply, measure brightness, pick the ramp step
                r, g, b = [min(255, ((p >> s) & 0xFF) * 255 // a) for s in (16, 8, 0)]
                lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                rr, gg, bb = RAMP_RGB[min(len(RAMP) - 1, int(lum * len(RAMP)))]
                cache[p] = (a << 24) | ((rr * a // 255) << 16) | ((gg * a // 255) << 8) | (bb * a // 255)
            new.append(cache[p])
        out.append((size, w, h, xh, yh, delay, new))
    return out


# --------------------------------------------------------------------------- main


def main():
    cursors_dir = os.path.join(OUT, "cursors")
    os.makedirs(cursors_dir, exist_ok=True)
    for entry in os.listdir(cursors_dir):            # start clean: names can move around
        os.remove(os.path.join(cursors_dir, entry))
    with open(os.path.join(OUT, "index.theme"), "w") as f:
        f.write("[Icon Theme]\nName=dungeonOS Cursor\n"
                "Comment=Final Fantasy Tactics items and a pixel art gauntlet\n")

    for name, (frames, hotspot, delay, aliases) in CURSORS.items():
        with open(os.path.join(cursors_dir, name), "wb") as f:
            f.write(encode(from_grids(frames, hotspot, delay)))
        for alias in aliases:
            os.symlink(name, os.path.join(cursors_dir, alias))
        print(f"{name}: {len(frames)} frame(s), {len(aliases)} aliases, hotspot "
              f"{hotspot(1) if callable(hotspot) else hotspot}")

    # Everything else: recolour the Miku theme's cursor, or repeat its alias.
    ours = set(CURSORS) | {a for _, _, _, aliases in CURSORS.values() for a in aliases}
    source_dir = os.path.join(os.path.dirname(OUT), SOURCE, "cursors")
    recoloured = aliased = 0
    for entry in sorted(os.listdir(source_dir)):
        if entry in ours:
            continue
        src = os.path.join(source_dir, entry)
        dest = os.path.join(cursors_dir, entry)
        if os.path.islink(src):
            target = os.readlink(src)
            os.symlink(target, dest)        # its target is either ours or recoloured below
            aliased += 1
        else:
            with open(dest, "wb") as f:
                f.write(encode(add_double_of_64(recolour(decode(src)))))
            recoloured += 1
    for entry in os.listdir(cursors_dir):
        assert os.path.exists(os.path.join(cursors_dir, entry)), f"broken link: {entry}"
    print(f"{recoloured} cursors recoloured from {SOURCE}, {aliased} aliases kept")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
