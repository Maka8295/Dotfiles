import sys
from PIL import Image
sys.path.insert(0, sys.argv[1])
import art
out = sys.argv[2]
def render(rows, scale):
    w = max(len(r) for r in rows); h = len(rows)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            c = art.PALETTE[ch]
            if c: im.putpixel((x, y), tuple(int(c[i:i+2], 16) for i in (1, 3, 5)) + (255,))
    return im.resize((w * scale, h * scale), Image.NEAREST)
names = [n for n in dir(art) if n.isupper() and isinstance(getattr(art, n), list)]
tiles = [render(getattr(art, n), 16) for n in names]
W = sum(t.width for t in tiles) + 40 * (len(tiles) + 1); H = max(t.height for t in tiles) + 80
for bgc, suffix in (((26, 24, 22, 255), "dark"), ((235, 235, 235, 255), "light")):
    sheet = Image.new("RGBA", (W, H), bgc); x = 40
    for t in tiles: sheet.alpha_composite(t, (x, 40)); x += t.width + 40
    sheet.save(f"{out}_{suffix}.png")
print(names)
