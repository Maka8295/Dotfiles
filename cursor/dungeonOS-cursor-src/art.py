# Pixel art for dungeonOS-cursor, on the same 32x32 grid as the Miku cursor.
# One character = one art pixel. Edit here, then run build.py.

PALETTE = {
    ".": None,          # transparent
    "K": "#141210",     # outline (bg_dark)
    "D": "#4A4540",     # deep steel shadow
    "S": "#6B6862",     # steel shade
    "M": "#8F8B81",     # steel
    "L": "#C8B8A0",     # light steel
    "W": "#DDD0BD",     # highlight
    "B": "#A88A5B",     # brass trim / rivets
    "b": "#7A5E47",     # brass shadow
    "R": "#7B4A3E",     # leather lining
}

# Index finger straight up — link / clickable pointer. Hotspot = fingertip.
POINT_UP = [
    "......KKK............",
    ".....KWLSK...........",
    ".....KWLSK...........",
    ".....KSSDK...........",
    ".....KWLSK...........",
    ".....KWLSK...........",
    ".....KSSDK...........",
    ".....KWLSKKKK........",
    ".....KWLSKWLSKKK.....",
    ".....KSSDKSSDKWLSKK..",
    "..KKKKWLSKWLSKSSDKLSK",
    ".KWLSKWLSKWLSKWLSKSDK",
    ".KWLMSKKKKKKKKKKKKKSK",
    ".KWLMSKBMMMBMMMBMMMSK",
    "..KWLMSKMMMMMMMMMMSDK",
    "..KWLLMSKMMMMMMMMMSDK",
    "...KWLLMMKMMMMMMMMSDK",
    "....KWLLMMMMMMMMMSDK.",
    ".....KWLMMMMMMMMMSDK.",
    ".....KKKKKKKKKKKKKKK.",
    "....KBBBBBBBBBBBBBBBK",
    "....KbbbbbbbbbbbbbbbK",
    "...KWLLMMMMMMMMMMMSSDK",
    "...KWLMMMMMMMMMMMMSSDK",
    "..KWLMMMMMMMMMMMMMSSDDK",
    "..KKKKKKKKKKKKKKKKKKKKK",
]
POINT_UP_HOTSPOT = (7, 0)

# Slanted gauntlet (2:1 slant, wrist upright). Not used right now — the main pointer
# is the FFT sword (fft-sword.png); swap it back in build.py to use this.
# hand-cleaned. Hotspot = fingertip.
POINT_DIAG = [
    "......KKK",
    ".....KWLSK",
    "......KWLSK",
    "......KSSDK",
    ".......KWLSK",
    ".......KWLSK",
    "........KSSDK",
    "........KWLSKKKK",
    ".........KWLSKWLSKKK",
    ".........KSSDKSSDKWLSKK",
    ".......KKKKWLSKWLSKSSDKLSK",
    "......KWLSKWLSKWLSKWLSKSDK",
    ".......KWLMSKKKKKKKKKKKKKSK",
    ".......KWLMSKBMMMBMMMBMMMSK",
    "........KKWLMSKMMMMMMMMMMSDK",
    ".........KWLLMSKMMMMMMMMMSDK",
    "..........KKWLLMKMMMMMMMMMSDK",
    "............KWLLMMMMMMMMMMSDK",
    ".............KKWLMMMMMMMMMSDK",
    "..............KKKKKKKKKKKKKKK",
    ".............KBBBBBBBBBBBBBBBK",
    ".............KbbbbbbbbbbbbbbbK",
    "............KWLLMMMMMMMMMMMSSDK",
    "............KWLMMMMMMMMMMMMSSDK",
    "...........KWLMMMMMMMMMMMMMSSDDK",
    "...........KKKKKKKKKKKKKKKKKKKKK",
]
POINT_DIAG_HOTSPOT = (6, 0)
