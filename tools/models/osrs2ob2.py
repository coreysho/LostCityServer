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

    # Per-face draw priorities. Dropping these (writing one global 0) made every imported
    # worn model draw BEFORE the player's torso (priority 2-3), so the torso painted over
    # the slayer helmet's face. Keep them exactly: 377 and OSRS use the same 0-11 scheme.
    pri = list(b[L['fpri']:L['fpri'] + fc]) if L['has_pri'] else None

    # Vertex labels (OSRS "packedVertexGroups"): which skeleton group each vertex follows.
    # Without them a worn model never moves with the player's animations. OSRS player
    # labels are identical to 377's (checked on rune helm/body/legs: same label sets).
    vlab = list(b[L['vgroup']:L['vgroup'] + vc]) if L['has_vgroup'] else None
    # Face labels (OSRS "packedTransparencyVertexGroups"): used by alpha animations.
    flab = list(b[L['tskin']:L['tskin'] + fc]) if L.get('has_tskin') else None

    # Which faces are textured. v2 (old style): render type bit 2, colour holds the texture
    # id. v3: a separate faceTextures section, stored as texture+1 (0 = none).
    tex = [False] * fc
    if L['ver'] == 2 and rtypes is not None:
        tex = [bool(t & 2) for t in rtypes]
    elif L['ver'] == 3 and L.get('has_ftex'):
        tp = P(b, L['ftexture'])
        tex = [tp.g2() != 0 for _ in range(fc)]

    # A textured face has no usable colour (377 has no texture for it), so it gets a flat
    # stand-in. Everything else keeps its colour.
    textured = 0
    finfo = [0] * fc
    alpha = list(alpha) if alpha is not None else None
    for i in range(fc):
        if tex[i]:
            colours[i] = TEXTURED_HSL; textured += 1
            continue
        t = (rtypes[i] & 3) if rtypes is not None else 0
        a = alpha[i] if alpha is not None else 0
        # OSRS Model.light(): alpha -1 (255) forces type 2, alpha -2 (254) forces type 3.
        if a == 254: t = 3
        if a == 255: t = 2
        if t == 1:
            finfo[i] = 1                           # flat shaded
        elif t == 2:                               # OSRS: faceColors3 = -2, never drawn
            if alpha is None: alpha = [0] * fc
            alpha[i] = 255
        elif t == 3:                               # OSRS: flat, colour 128
            finfo[i] = 1; colours[i] = 128
            if alpha is not None: alpha[i] = 0

    return dict(ver=L['ver'], vcount=vc, fcount=fc, vx=vx, vy=vy, vz=vz,
                fa=fa, fb=fb, fc=fcc, colour=colours, alpha=alpha,
                textured=textured, priority=L['pri'], pri=pri,
                vlab=vlab, flab=flab, finfo=finfo if any(finfo) else None)


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
    pri = m.get('pri')
    if pri is not None and len(set(pri)) == 1:
        glob_pri, pri = pri[0], None               # uniform -> global, like the source
    else:
        glob_pri = m.get('priority', 0) if m.get('priority', 0) != 255 else 0
    flab = m.get('flab'); vlab = m.get('vlab'); finfo = m.get('finfo')

    # Section order is Model.java's walk, not the trailer's flag order:
    # vflags, ftypes, [priorities], [face labels], [face info], [vertex labels],
    # [alpha], face data, colours, textures, x, y, z.
    out = bytearray()
    out += vflags
    out += ftypes
    if pri is not None:   out += bytes(pri)
    if flab is not None:  out += bytes(flab)
    if finfo is not None: out += bytes(finfo)
    if vlab is not None:  out += bytes(vlab)
    if alpha is not None:
        out += bytes(a & 0xFF for a in alpha)
    out += fdata
    out += colours
    out += xb + yb + zb

    trailer = bytearray()
    g2 = lambda v: bytes([(v >> 8) & 0xFF, v & 0xFF])
    trailer += g2(vc) + g2(fc)
    trailer += bytes([0])                       # texture count
    trailer += bytes([1 if finfo is not None else 0])
    trailer += bytes([255 if pri is not None else glob_pri])
    trailer += bytes([1 if alpha is not None else 0])
    trailer += bytes([1 if flab is not None else 0])
    trailer += bytes([1 if vlab is not None else 0])
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
    pri_o = o
    if f_pri == 255: o += fc
    flab_o = o
    if f_flab == 1: o += fc
    finfo_o = o
    if f_tex == 1:  o += fc
    vlab_o = o
    if f_vlab == 1: o += vc
    alpha_o = o
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
                fa=fa, fb=fb, fc=fcc, colour=colour,
                pri=list(b[pri_o:pri_o + fc]) if f_pri == 255 else [f_pri] * fc,
                flab=list(b[flab_o:flab_o + fc]) if f_flab == 1 else None,
                finfo=list(b[finfo_o:finfo_o + fc]) if f_tex == 1 else None,
                vlab=list(b[vlab_o:vlab_o + vc]) if f_vlab == 1 else None,
                alpha=list(b[alpha_o:alpha_o + fc]) if f_alpha == 1 else None)


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
    want_pri = m['pri'] if m.get('pri') is not None else [m.get('priority', 0) if m.get('priority', 0) != 255 else 0] * m['fcount']
    if r['pri'] != want_pri:
        return False, 'priorities differ'
    if (r['vlab'] or None) != (m.get('vlab') or None):
        return False, 'vertex labels differ'
    if (r['flab'] or None) != (m.get('flab') or None):
        return False, 'face labels differ'
    if (r['finfo'] or None) != (m.get('finfo') or None):
        return False, 'face info differs'
    ma = m['alpha'] if (m.get('alpha') and any(m['alpha'])) else None
    if (r['alpha'] or None) != ma:
        return False, 'alpha differs'
    return True, 'ok'


def convert_checked(b):
    """Decode, encode, and verify in one call. Returns (ob2_bytes, model, reason)."""
    m = decode(b)
    if m is None: return None, None, 'layout does not reconcile'
    ob2 = encode(m)
    ok, why = roundtrip(ob2, m)
    if not ok: return None, m, why
    return ob2, m, 'ok'
