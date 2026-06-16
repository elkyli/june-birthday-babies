#!/usr/bin/env python3
"""
Remove the solid white background from a character PNG and trim the margins.

Pure standard library (zlib only) — no PIL.
  python3 assets/_cutout.py <input.png> <output.png>

How it works:
  - Decodes an 8-bit RGBA PNG.
  - Flood-fills from the image borders across "light" pixels (min channel high),
    so ONLY background white connected to the edge is removed — interior whites
    (GAP letters, drawstrings, teeth) are untouched.
  - Feathers the edge alpha for a clean (non-jagged) cutout.
  - Auto-crops to the figure's bounding box with a little padding.
"""
import struct, zlib, sys
from collections import deque


def read_rgba(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, W, H, idat = 8, 0, 0, bytearray()
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            W, H, bd, ct = struct.unpack(">IIBB", chunk[:10])
            assert bd == 8 and ct == 6, "expected 8-bit RGBA"
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break
        pos += 12 + ln

    raw = zlib.decompress(bytes(idat))
    bpp, stride = 4, W * 4
    out = bytearray(W * H * 4)
    prev = bytearray(stride)
    p = 0
    for y in range(H):
        ft = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if ft == 1:      # Sub
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ft == 2:    # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:    # Average
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:    # Paeth
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return W, H, out


def cutout(W, H, px, lo=200, hi=242):
    """Border-connected white -> transparent, feathered between lo..hi."""
    visited = bytearray(W * H)
    dq = deque()

    def lightish(i):
        idx = i * 4
        return min(px[idx], px[idx + 1], px[idx + 2]) >= lo

    def push(x, y):
        i = y * W + x
        if not visited[i] and lightish(i):
            visited[i] = 1
            dq.append((x, y))

    for x in range(W):
        push(x, 0); push(x, H - 1)
    for y in range(H):
        push(0, y); push(W - 1, y)
    while dq:
        x, y = dq.popleft()
        if x + 1 < W: push(x + 1, y)
        if x - 1 >= 0: push(x - 1, y)
        if y + 1 < H: push(x, y + 1)
        if y - 1 >= 0: push(x, y - 1)

    span = hi - lo
    for i in range(W * H):
        if visited[i]:
            idx = i * 4
            m = min(px[idx], px[idx + 1], px[idx + 2])
            if m >= hi:
                px[idx + 3] = 0
            else:                       # feather the thin halo near the figure
                a = int(255 * (hi - m) / span)
                px[idx + 3] = 0 if a < 0 else (255 if a > 255 else a)
    return px


def trim(W, H, px, pad=12):
    """Crop to the bounding box of visible (alpha>8) pixels, plus padding."""
    minx, miny, maxx, maxy = W, H, -1, -1
    for y in range(H):
        row = y * W * 4
        for x in range(W):
            if px[row + x * 4 + 3] > 8:
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
    if maxx < 0:
        return W, H, px
    minx = max(0, minx - pad); miny = max(0, miny - pad)
    maxx = min(W - 1, maxx + pad); maxy = min(H - 1, maxy + pad)
    nw, nh = maxx - minx + 1, maxy - miny + 1
    out = bytearray(nw * nh * 4)
    for y in range(nh):
        src = ((miny + y) * W + minx) * 4
        out[y * nw * 4:(y + 1) * nw * 4] = px[src:src + nw * 4]
    return nw, nh, out


def write_rgba(path, W, H, px):
    raw = bytearray()
    stride = W * 4
    for y in range(H):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, d):
        return struct.pack(">I", len(d)) + tag + d + struct.pack(">I", zlib.crc32(tag + d) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
                           chunk(b"IDAT", comp) + chunk(b"IEND", b""))


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    W, H, px = read_rgba(src)
    cutout(W, H, px)
    W, H, px = trim(W, H, px)
    write_rgba(dst, W, H, px)
    print(f"{src} -> {dst}  ({W}x{H}, transparent + trimmed)")
