#!/usr/bin/env python3
"""Convert an OSRS model (type 2 / type 3) into a 317-family .ob2 the 377 client reads.

Unlike the 474 pipeline, this is a real re-encode: decode the OSRS geometry off the
verified layout in osrsmodel.py, then write it back out in the older format.

Checked three ways, because a model that decodes without throwing can still be wrong:
  1. the source layout must reconcile exactly (osrsmodel.py refuses otherwise),
  2. the .ob2 we write is re-read with ob2render's own reader and the geometry compared
     vertex for vertex and face for face,
  3. render it and look at it.
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osrsmodel import P, layout, version

MAX_V = MAX_F = 4096          # dash3d/Model.java hard limits
TEXTURED_HSL = 6070           # flat stand-in for a textured face; 377 has no texture here


# ------------------------------------------------------------------ decode
def decode(b):
    """Geometry out of an OSRS model. Returns None if the layout does not reconcile."""
    L = layout(b)
    if L is None or L['walked'] != L['body']:
        return None
    vc, fc = L['vc'], L['fc']

    vf = P(b, L['vflag'])
    xs, ys, zs = P(b, L['xo']), P(b, L['yo']), P(b, L['zo'])
    vx, vy, vz = [], [], []
    px = py = pz = 0
    for _ in range(vc):
        fl = vf.g1()
        px += xs.gsmart() if fl & 1 else 0
        py += ys.gsmart() if fl & 2 else 0
        pz += zs.gsmart() if fl & 4 else 0
        vx.append(px); vy.append(py); vz.append(pz)

    col = P(b, L['colour'])
    colours = [col.g2() for _ in range(fc)]

    rtypes = None
    if L['has_rtype']:
        rt = P(b, L['frt'])
        rtypes = [rt.g1() for _ in range(fc)]

    ft = P(b, L['ftype'])
    fd = P(b, L['fdata'])
    fa, fb, fcc = [], [], []
    a = bb = c = trip = 0
    for _ in range(fc):
        t = ft.g1()
        if t == 1:
            a = fd.gsmart() + trip; bb = fd.gsmart() + a; c = fd.gsmart() + bb; trip = c
        elif t == 2:
            bb = c; c = fd.gsmart() + trip; trip = c
        elif t == 3:
            a = c; c = fd.gsmart() + trip; trip = c
        elif t == 4:
            a, bb = bb, a; c = fd.gsmart() + trip; trip = c
        fa.append(a); fb.append(bb); fcc.append(c)

    alpha = None
    if L['has_alpha']:
        ap = P(b, L['falpha'])
        alpha = [ap.g1() for _ in range(fc)]

    # A face whose render type has bit 2 set had its colour overwritten with the texture
    # id (the original colour is simply not in the file), so it gets a flat stand-in.
    textured = 0
    if rtypes is not None:
        for i, t in enumerate(rtypes):
            if t & 2:
                colours[i] = TEXTURED_HSL; textured += 1

    return dict(ver=L['ver'], vcount=vc, fcount=fc, vx=vx, vy=vy, vz=vz,
                fa=fa, fb=fb, fc=fcc, colour=colours, alpha=alpha,
                textured=textured, priority=L['pri'])


# ------------------------------------------------------------------ encode
def wsmart(v):
    if -64 <= v < 64:
        return bytes([v + 64])
    if -16384 <= v < 16384:
        x = v + 49152
        return bytes([(x >> 8) & 0xFF, x & 0xFF])
    raise ValueError(f'value {v} does not fit a gsmart')


def encode(m, keep_alpha=True):
    """Write 317-family .ob2 bytes. Section order follows Model.java's own walk."""
    vc, fc = m['vcount'], m['fcount']
    if vc > MAX_V or fc > MAX_F:
        raise ValueError(f'{vc} verts / {fc} faces exceeds the client limit of {MAX_V}/{MAX_F}')

    vflags = bytearray(); xb = bytearray(); yb = bytearray(); zb = bytearray()
    px = py = pz = 0
    for i in range(vc):
        dx, dy, dz = m['vx'][i] - px, m['vy'][i] - py, m['vz'][i] - pz
        fl = 0
        if dx: fl |= 1; xb += wsmart(dx)
        if dy: fl |= 2; yb += wsmart(dy)
        if dz: fl |= 4; zb += wsmart(dz)
        vflags.append(fl)
        px, py, pz = m['vx'][i], m['vy'][i], m['vz'][i]

    # every face written as a full triple (type 1) - always valid, and it keeps the
    # writer independent of however the source happened to delta-encode its faces
    ftypes = bytearray(); fdata = bytearray()
    trip = 0
    for i in range(fc):
        a, b_, c = m['fa'][i], m['fb'][i], m['fc'][i]
        ftypes.append(1)
        fdata += wsmart(a - trip) + wsmart(b_ - a) + wsmart(c - b_)
        trip = c

    colours = bytearray()
    for v in m['colour']:
        colours += bytes([(v >> 8) & 0xFF, v & 0xFF])

    alpha = m['alpha'] if (keep_alpha and m['alpha'] and any(m['alpha'])) else None

    # Section order is Model.java's walk, not the trailer's flag order:
    # vflags, ftypes, [priorities], [face labels], [face info], [vertex labels],
    # [alpha], face data, colours, textures, x, y, z.
    out = bytearray()
    out += vflags
    out += ftypes
    if alpha is not None:
        out += bytes(a & 0xFF for a in alpha)
    out += fdata
    out += colours
    out += xb + yb + zb

    trailer = bytearray()
    g2 = lambda v: bytes([(v >> 8) & 0xFF, v & 0xFF])
    trailer += g2(vc) + g2(fc)
    trailer += bytes([0])                       # texture count
    trailer += bytes([0])                       # no face info section
    trailer += bytes([0])                       # global priority 0 (not per-face)
    trailer += bytes([1 if alpha is not None else 0])
    trailer += bytes([0])                       # no face labels
    trailer += bytes([0])                       # no vertex labels
    trailer += g2(len(xb)) + g2(len(yb)) + g2(len(zb)) + g2(len(fdata))
    return bytes(out + trailer)


def convert(b):
    m = decode(b)
    if m is None: return None, None
    return encode(m), m


# ------------------------------------------------------------------ verify
def parse_ob2(b):
    """Independent 317-family reader - deliberately NOT ob2render's, and numpy-free so
    verification runs anywhere. Mirrors Model.java's section walk."""
    h = P(b, len(b) - 18)
    vc, fc = h.g2(), h.g2()
    tc = h.g1()
    f_tex, f_pri, f_alpha, f_flab, f_vlab = h.g1(), h.g1(), h.g1(), h.g1(), h.g1()
    xlen, ylen, zlen, flen = h.g2(), h.g2(), h.g2(), h.g2()

    o = 0
    vflag_o = o; o += vc
    ftype_o = o; o += fc
    if f_pri == 255: o += fc
    if f_flab == 1: o += fc
    if f_tex == 1:  o += fc
    if f_vlab == 1: o += vc
    if f_alpha == 1: o += fc
    fdata_o = o; o += flen
    colour_o = o; o += fc * 2
    o += tc * 6
    x_o = o; o += xlen
    y_o = o; o += ylen
    z_o = o; o += zlen
    if o != len(b) - 18:
        raise ValueError(f'section walk {o} != body {len(b) - 18}')

    vf, xs, ys, zs = P(b, vflag_o), P(b, x_o), P(b, y_o), P(b, z_o)
    vx, vy, vz = [], [], []
    px = py = pz = 0
    for _ in range(vc):
        fl = vf.g1()
        px += xs.gsmart() if fl & 1 else 0
        py += ys.gsmart() if fl & 2 else 0
        pz += zs.gsmart() if fl & 4 else 0
        vx.append(px); vy.append(py); vz.append(pz)

    cp = P(b, colour_o)
    colour = [cp.g2() for _ in range(fc)]

    ft, fd = P(b, ftype_o), P(b, fdata_o)
    fa, fb, fcc = [], [], []
    a = bb = c = trip = 0
    for _ in range(fc):
        t = ft.g1()
        if t == 1:
            a = fd.gsmart() + trip; bb = fd.gsmart() + a; c = fd.gsmart() + bb; trip = c
        elif t == 2:
            bb = c; c = fd.gsmart() + trip; trip = c
        elif t == 3:
            a = c; c = fd.gsmart() + trip; trip = c
        elif t == 4:
            a, bb = bb, a; c = fd.gsmart() + trip; trip = c
        fa.append(a); fb.append(bb); fcc.append(c)
    return dict(vcount=vc, fcount=fc, vx=vx, vy=vy, vz=vz,
                fa=fa, fb=fb, fc=fcc, colour=colour)


def roundtrip(ob2_bytes, m):
    """Re-read our own output and compare geometry exactly. Returns (ok, reason)."""
    try:
        r = parse_ob2(ob2_bytes)
    except Exception as e:
        return False, f'reread failed: {e}'
    if r['vcount'] != m['vcount'] or r['fcount'] != m['fcount']:
        return False, 'counts differ'
    for i in range(m['vcount']):
        if (r['vx'][i], r['vy'][i], r['vz'][i]) != (m['vx'][i], m['vy'][i], m['vz'][i]):
            return False, f'vertex {i} differs'
    for i in range(m['fcount']):
        if (r['fa'][i], r['fb'][i], r['fc'][i]) != (m['fa'][i], m['fb'][i], m['fc'][i]):
            return False, f'face {i} differs'
        if r['colour'][i] != m['colour'][i]:
            return False, f'colour {i} differs'
    return True, 'ok'


def convert_checked(b):
    """Decode, encode, and verify in one call. Returns (ob2_bytes, model, reason)."""
    m = decode(b)
    if m is None: return None, None, 'layout does not reconcile'
    ob2 = encode(m)
    ok, why = roundtrip(ob2, m)
    if not ok: return None, m, why
    return ob2, m, 'ok'
