#!/usr/bin/env python3
"""
Generates glossy Barbie-style PLACEHOLDER PNGs for the birthday game.
Pure standard-library (zlib only) — no PIL needed.

Re-run with:  python3 assets/_make_placeholders.py
You can safely delete this file once you drop in real art.
Output filenames are intentionally fixed so real art can replace them 1:1.
"""
import os, struct, zlib, math

W = H = 512
OUT = os.path.dirname(os.path.abspath(__file__))


def png(path, px):
    """px is a flat bytearray of RGBA, length W*H*4."""
    raw = bytearray()
    stride = W * 4
    for y in range(H):
        raw.append(0)  # filter type 0
        raw.extend(px[y * stride:(y + 1) * stride])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)  # 8-bit RGBA
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def blend(px, x, y, rgb, alpha=1.0):
    if x < 0 or x >= W or y < 0 or y >= H:
        return
    i = (y * W + x) * 4
    for k in range(3):
        px[i + k] = int(px[i + k] * (1 - alpha) + rgb[k] * alpha)
    px[i + 3] = max(px[i + 3], int(255 * alpha))


def rounded_rect_alpha(x, y, rx0, ry0, rx1, ry1, r):
    """soft-edged rounded-rect coverage 0..1 (anti-aliased)."""
    cx = min(max(x, rx0 + r), rx1 - r)
    cy = min(max(y, ry0 + r), ry1 - r)
    d = math.hypot(x - cx, y - cy)
    return max(0.0, min(1.0, (r - d) + 0.5))


def disc(px, cx, cy, rad, rgb, alpha=1.0):
    for y in range(int(cy - rad - 1), int(cy + rad + 2)):
        for x in range(int(cx - rad - 1), int(cx + rad + 2)):
            d = math.hypot(x - cx, y - cy)
            cov = max(0.0, min(1.0, (rad - d) + 0.5))
            if cov > 0:
                blend(px, x, y, rgb, cov * alpha)


def base_tile(top, bot):
    """glossy rounded tile with vertical gradient + top gloss highlight."""
    px = bytearray(W * H * 4)  # transparent
    margin, radius = 14, 70
    for y in range(H):
        t = y / H
        col = lerp(top, bot, t)
        for x in range(W):
            a = rounded_rect_alpha(x, y, margin, margin, W - margin, H - margin, radius)
            if a <= 0:
                continue
            # glossy highlight band near the top
            gloss = max(0.0, 1 - abs(y - H * 0.22) / (H * 0.5))
            c = lerp(col, (255, 255, 255), gloss * 0.22)
            blend(px, x, y, c, a)
    # white outline
    for y in range(H):
        for x in range(W):
            a = rounded_rect_alpha(x, y, margin, margin, W - margin, H - margin, radius)
            edge = 1 - abs(a - 0.5) * 2  # peaks at the border
            if 0.5 < a < 1.0 and a > 0.5:
                pass
    return px


def outline(px, color=(255, 255, 255), width=7):
    margin, radius = 14, 70
    for y in range(H):
        for x in range(W):
            a = rounded_rect_alpha(x, y, margin, margin, W - margin, H - margin, radius)
            if 0 < a < 1:  # antialiased border ring
                blend(px, x, y, color, a)
    # thicken: draw a slightly inset ring
    m2, r2 = margin + width, radius - width
    for y in range(H):
        for x in range(W):
            ao = rounded_rect_alpha(x, y, margin, margin, W - margin, H - margin, radius)
            ai = rounded_rect_alpha(x, y, m2, m2, W - m2, H - m2, r2)
            ring = max(0.0, ao - ai)
            if ring > 0:
                blend(px, x, y, color, ring)


def gift_box(px, color, ribbon=(255, 255, 255)):
    """draws a centered wrapped gift with a bow."""
    bx0, by0, bx1, by1 = 150, 220, 362, 410
    # box body
    for y in range(by0, by1):
        for x in range(bx0, bx1):
            shade = 1 - (x - bx0) / (bx1 - bx0) * 0.18
            blend(px, x, y, tuple(int(c * shade) for c in color), 1.0)
    # vertical ribbon
    for y in range(by0, by1):
        for x in range(246, 266):
            blend(px, x, y, ribbon, 1.0)
    # lid
    for y in range(200, 224):
        for x in range(140, 372):
            blend(px, x, y, tuple(int(c * 0.92) for c in color), 1.0)
    # horizontal ribbon on lid
    for y in range(200, 224):
        for x in range(246, 266):
            blend(px, x, y, ribbon, 1.0)
    # bow (two loops)
    disc(px, 232, 184, 30, ribbon)
    disc(px, 280, 184, 30, ribbon)
    disc(px, 232, 184, 14, color)
    disc(px, 280, 184, 14, color)
    disc(px, 256, 190, 14, ribbon)


def face(px, skin, hair):
    """a simple cute face for the character cards."""
    # hair back
    disc(px, 256, 250, 150, hair)
    # face
    disc(px, 256, 260, 120, skin)
    # cheeks
    disc(px, 200, 290, 24, (255, 160, 190), 0.55)
    disc(px, 312, 290, 24, (255, 160, 190), 0.55)
    # eyes
    disc(px, 214, 250, 16, (60, 40, 70))
    disc(px, 298, 250, 16, (60, 40, 70))
    disc(px, 219, 245, 6, (255, 255, 255))
    disc(px, 303, 245, 6, (255, 255, 255))
    # smile
    for a in range(20, 160):
        rad = a * math.pi / 180
        x = 256 + math.cos(rad) * 46
        y = 300 + math.sin(rad) * 30
        disc(px, x, y, 5, (210, 70, 110))
    # hair fringe on top
    disc(px, 256, 150, 120, hair)
    disc(px, 256, 230, 130, hair, 0.0)  # no-op keeps face clear
    # little crown
    for i, ox in enumerate((-60, -20, 20, 60)):
        disc(px, 256 + ox, 120, 18, (255, 215, 80))


# ---- character cards ----
def make_character(name, skin, hair, top, bot):
    px = base_tile(top, bot)
    face(px, skin, hair)
    outline(px)
    png(os.path.join(OUT, name), px)
    print("wrote", name)


# ---- gift tiles ----
GIFT_PALETTE = [
    ((255, 105, 180), (255, 20, 147)),
    ((186, 104, 255), (138, 43, 226)),
    ((80, 200, 255), (0, 140, 220)),
    ((255, 190, 60), (255, 140, 0)),
    ((120, 230, 160), (20, 180, 120)),
    ((255, 130, 130), (230, 40, 90)),
]


def make_gift(name, idx):
    top, bot = GIFT_PALETTE[idx % len(GIFT_PALETTE)]
    # softer tile bg, vivid box
    px = base_tile(lerp(top, (255, 255, 255), 0.45), lerp(bot, (255, 255, 255), 0.3))
    gift_box(px, bot)
    outline(px)
    png(os.path.join(OUT, name), px)
    print("wrote", name)


if __name__ == "__main__":
    N = 6  # gifts per character — keep in sync with index.html GIFT_COUNT
    make_character("june.png", (255, 224, 196), (90, 50, 30), (255, 150, 200), (255, 80, 160))
    make_character("jordyn.png", (245, 210, 180), (40, 30, 60), (200, 130, 255), (150, 60, 230))
    for i in range(1, N + 1):
        make_gift(f"june-gift-{i}.png", i - 1)
    for i in range(1, N + 1):
        make_gift(f"jordyn-gift-{i}.png", i - 1)
    print("done — N =", N)
