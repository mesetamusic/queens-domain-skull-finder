"""Draws a simple silver skull and writes skull.ico (16-256 px, PNG-in-ICO). No dependencies."""
import os, struct, zlib


def shade(u, v):
    """u, v in [-1, 1] (v down). Returns RGBA."""
    def ell(cx, cy, rx, ry): return ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2
    cranium = ell(0, -0.12, 0.78, 0.72) <= 1
    jaw = abs(u) <= 0.46 and 0.3 <= v <= 0.82 and ell(0, 0.55, 0.5, 0.45) <= 1.15
    if not (cranium or jaw): return (0, 0, 0, 0)
    eye = ell(-0.33, 0.02, 0.21, 0.24) <= 1 or ell(0.33, 0.02, 0.21, 0.24) <= 1
    nose = 0.28 <= v <= 0.46 and abs(u) <= (v - 0.28) * 0.55 + 0.02
    teeth = 0.6 <= v <= 0.78 and abs(u) <= 0.36 and (int((u + 0.36) / 0.12) % 2 == 1 and abs(((u + 0.36) % 0.12) - 0.06) < 0.012)
    gum = abs(v - 0.6) < 0.025 and abs(u) <= 0.38
    if eye or nose: return (28, 32, 44, 255)
    if teeth or gum: return (90, 98, 112, 255)
    light = max(0.0, min(1.0, 0.95 - 0.35 * (u + 0.2) ** 2 - 0.3 * max(0, v) - 0.15 * max(0, -v - 0.6)))
    g = int(150 + 95 * light)
    return (g - 6, g, min(255, g + 10), 255)


def png(size, ss=4):
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    u = ((x + (sx + .5) / ss) / size) * 2 - 1
                    v = ((y + (sy + .5) / ss) / size) * 2 - 1
                    c = shade(u * 1.08, v * 1.08)
                    for i in range(3): acc[i] += c[i] * c[3]
                    acc[3] += c[3]
            a = acc[3] / (ss * ss)
            row += bytes([int(acc[i] / acc[3]) if acc[3] else 0 for i in range(3)] + [int(a)])
        rows.append(bytes(row))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [png(s) for s in sizes]
    hdr = struct.pack("<HHH", 0, 1, len(sizes)); off = 6 + 16 * len(sizes); dirs = b""
    for s, im in zip(sizes, imgs):
        dirs += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(im), off); off += len(im)
    with open(os.path.join(here, "skull.ico"), "wb") as fh: fh.write(hdr + dirs + b"".join(imgs))
    with open(os.path.join(here, "..", "docs", "icon.png"), "wb") as fh: fh.write(png(128))


if __name__ == "__main__":
    main()
