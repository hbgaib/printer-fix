#!/usr/bin/env python3
"""Build an RGB output ICC profile that makes Gutenprint's ink output for the
Canon iP2700 imitate Canon's own driver (cnijfilter, same print mode).

Inputs are ink measurements of the same 9x9x9 RGB grid rendered by both drivers
(decoded from the printer's ESC (F raster data, see measure.py):
  grid_gp.json  Gutenprint   [[r,g,b,C,M,Y,K], ...]
  grid_cn.json  Canon driver

The profile's B2A tables map PCS Lab -> sRGB -> corrected RGB', where RGB' is the
input Gutenprint needs to lay down the ink Canon would. Near-neutral colours are
left alone so grey and black text keep Gutenprint's pure-K rendering.

usage: build_profile.py grid_gp.json grid_cn.json out.icc
"""
import json, struct, sys, time

LEVELS = 9
STEP = 255 / (LEVELS - 1)
SCALE = (0.5, 0.5, 1.0, 1.0)      # C,M are 2-bit (0..2 used), Y,K 1-bit
B2A_GRID = 41
A2B_GRID = 17
CHROMA_LO, CHROMA_HI = 0.08, 0.25  # blend: no correction below, full above


def load(path):
    t = {}
    for r in json.load(open(path)):
        t[tuple(r[:3])] = [v * s for v, s in zip(r[3:], SCALE)]
    return t


def make_interp(table):
    lv = [round(i * STEP) for i in range(LEVELS)]
    def ink(r, g, b):
        idx, frac = [], []
        for v in (r, g, b):
            p = min(max(v, 0), 255) / STEP
            i = min(int(p), LEVELS - 2)
            idx.append(i); frac.append(p - i)
        out = [0.0] * 4
        for dr in (0, 1):
            wr = frac[0] if dr else 1 - frac[0]
            for dg in (0, 1):
                wg = frac[1] if dg else 1 - frac[1]
                for db in (0, 1):
                    w = wr * wg * (frac[2] if db else 1 - frac[2])
                    if w:
                        v = table[(lv[idx[0] + dr], lv[idx[1] + dg], lv[idx[2] + db])]
                        for c in range(4):
                            out[c] += w * v[c]
        return out
    return ink


def solve(gp, target, start):
    """Find RGB' with gp(RGB') closest to target ink (coordinate descent)."""
    best = list(start)
    cost = lambda p: sum((a - b) ** 2 for a, b in zip(gp(*p), target))
    bc = cost(best)
    for step in (32, 16, 8, 4, 2, 1, 0.5):
        improved = True
        while improved:
            improved = False
            for ax in range(3):
                for s in (-step, step):
                    p = list(best); p[ax] = min(255, max(0, p[ax] + s))
                    c = cost(p)
                    if c < bc - 1e-12:
                        best, bc, improved = p, c, True
    return best


def build_correction(gp, cn, n=17):
    """Correction f on an n^3 RGB grid; returns lookup with trilinear interp."""
    pts = [i * 255 / (n - 1) for i in range(n)]
    f = {}
    for i, r in enumerate(pts):
        for j, g in enumerate(pts):
            for k, b in enumerate(pts):
                f[(i, j, k)] = solve(gp, cn(r, g, b), (r, g, b))
    def apply(r, g, b):
        idx, frac = [], []
        for v in (r, g, b):
            p = min(max(v, 0), 255) / 255 * (n - 1)
            i = min(int(p), n - 2)
            idx.append(i); frac.append(p - i)
        out = [0.0] * 3
        for dr in (0, 1):
            wr = frac[0] if dr else 1 - frac[0]
            for dg in (0, 1):
                wg = frac[1] if dg else 1 - frac[1]
                for db in (0, 1):
                    w = wr * wg * (frac[2] if db else 1 - frac[2])
                    if w:
                        v = f[(idx[0] + dr, idx[1] + dg, idx[2] + db)]
                        for c in range(3):
                            out[c] += w * v[c]
        chroma = (max(r, g, b) - min(r, g, b)) / 255
        w = min(1, max(0, (chroma - CHROMA_LO) / (CHROMA_HI - CHROMA_LO)))
        w = w * w * (3 - 2 * w)
        return [x + w * (y - x) for x, y in zip((r, g, b), out)]
    return apply


# --- sRGB <-> Lab (D50, as in ICC sRGB profiles) ---
M_RGB2XYZ = ((0.4360747, 0.3850649, 0.1430804),
             (0.2225045, 0.7168786, 0.0606169),
             (0.0139322, 0.0971045, 0.7141733))
M_XYZ2RGB = ((3.1338561, -1.6168667, -0.4906146),
             (-0.9787684, 1.9161415, 0.0334540),
             (0.0719453, -0.2289914, 1.4052427))
WHITE = (0.9642, 1.0, 0.8249)


def srgb_to_lab(rgb):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    xyz = [sum(m * v for m, v in zip(row, lin)) for row in M_RGB2XYZ]
    f = [t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
         for t in (x / w for x, w in zip(xyz, WHITE))]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def lab_to_srgb(L, a, b):
    fy = (L + 16) / 116; fx = fy + a / 500; fz = fy - b / 200
    inv = lambda t: t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)
    xyz = [inv(fx) * WHITE[0], inv(fy) * WHITE[1], inv(fz) * WHITE[2]]
    lin = [sum(m * v for m, v in zip(row, xyz)) for row in M_XYZ2RGB]
    out = []
    for c in lin:
        c = min(max(c, 0.0), 1.0)
        out.append(12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)
    return out


# --- ICC v2 writer ---
def s15(v):
    return struct.pack('>i', round(v * 65536))


def lut16(in_ch, out_ch, grid, values):
    head = b'mft2' + b'\0' * 4 + struct.pack('>BBBB', in_ch, out_ch, grid, 0)
    head += b''.join(s15(1 if i % 4 == 0 else 0) for i in range(9))
    head += struct.pack('>HH', 2, 2)
    tables_in = struct.pack('>HH', 0, 65535) * in_ch
    tables_out = struct.pack('>HH', 0, 65535) * out_ch
    clut = b''.join(struct.pack('>H', min(65535, max(0, round(v)))) for v in values)
    return head + tables_in + clut + tables_out


def text_desc(s):
    a = s.encode('ascii') + b'\0'
    return b'desc' + b'\0' * 4 + struct.pack('>I', len(a)) + a + struct.pack('>II', 0, 0) + b'\0' * 70


def write_icc(path, a2b, b2a, desc):
    tags = [(b'desc', text_desc(desc)),
            (b'cprt', b'text' + b'\0' * 4 + b'No copyright, use freely\0'),
            (b'wtpt', b'XYZ ' + b'\0' * 4 + b''.join(s15(v) for v in WHITE)),
            (b'A2B0', a2b), (b'B2A0', b2a)]
    shared = {b'A2B1': b'A2B0', b'A2B2': b'A2B0', b'B2A1': b'B2A0', b'B2A2': b'B2A0'}
    n = len(tags) + len(shared)
    off = 128 + 4 + 12 * n
    table, data, where = [], b'', {}
    for sig, blob in tags:
        while (off + len(data)) % 4:
            data += b'\0'
        where[sig] = (off + len(data), len(blob))
        table.append((sig, *where[sig]))
        data += blob
    for sig, src in shared.items():
        table.append((sig, *where[src]))
    body = struct.pack('>I', n) + b''.join(s + struct.pack('>II', o, l) for s, o, l in table) + data
    size = 128 + len(body)
    t = time.gmtime()
    hdr = struct.pack('>I', size) + b'lcms' + struct.pack('>I', 0x02100000) + b'prtr' + b'RGB ' + b'Lab '
    hdr += struct.pack('>6H', t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
    hdr += b'acsp' + b'\0' * 24 + struct.pack('>I', 0) + b''.join(s15(v) for v in WHITE)
    hdr += b'\0' * (128 - len(hdr))
    open(path, 'wb').write(hdr + body)


def main():
    gp_t, cn_t, out = sys.argv[1:4]
    gp, cn = make_interp(load(gp_t)), make_interp(load(cn_t))
    f = build_correction(gp, cn)

    # B2A: Lab grid (v2 lut16 encoding) -> corrected device RGB
    b2a = []
    for i in range(B2A_GRID):
        L = i * 65535 / (B2A_GRID - 1) / 65280 * 100
        for j in range(B2A_GRID):
            a = j * 65535 / (B2A_GRID - 1) / 256 - 128
            for k in range(B2A_GRID):
                b = k * 65535 / (B2A_GRID - 1) / 256 - 128
                rgb = [c * 255 for c in lab_to_srgb(min(L, 100), a, b)]
                b2a += [v / 255 * 65535 for v in f(*rgb)]
    # A2B: plain sRGB -> Lab (only used for proofing / black point)
    a2b = []
    for i in range(A2B_GRID):
        for j in range(A2B_GRID):
            for k in range(A2B_GRID):
                L, a, b = srgb_to_lab([v / (A2B_GRID - 1) for v in (i, j, k)])
                a2b += [L / 100 * 65280, (a + 128) * 256, (b + 128) * 256]
    write_icc(out, lut16(3, 3, A2B_GRID, a2b), lut16(3, 3, B2A_GRID, b2a),
              'Canon iP2700 Gutenprint plain - Canon-matched colour')
    for name, rgb in [('hijau logo', (135, 193, 35)), ('emas', (192, 142, 0)),
                      ('biru', (40, 90, 200)), ('abu50', (128, 128, 128)), ('hitam', (0, 0, 0))]:
        print(f'{name:11s} {rgb} -> {tuple(round(v) for v in f(*rgb))}')


if __name__ == '__main__':
    main()
