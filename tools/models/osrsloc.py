#!/usr/bin/env python3
"""OSRS loc (object) config decoder - idx2 group 6, RuneLite ObjectLoader (rev 220+ sound data).
Every record must end exactly on its 0 terminator or it is rejected."""
import struct

class _R:
    def __init__(s, b): s.b = b; s.p = 0
    def u1(s): v = s.b[s.p]; s.p += 1; return v
    def s1(s): v = s.u1(); return v - 256 if v > 127 else v
    def u2(s): v = (s.b[s.p] << 8) | s.b[s.p+1]; s.p += 2; return v
    def s2(s): v = s.u2(); return v - 65536 if v > 32767 else v
    def i4(s): v = struct.unpack('>i', s.b[s.p:s.p+4])[0]; s.p += 4; return v
    def string(s):
        e = s.b.index(0, s.p); v = s.b[s.p:e].decode('latin-1'); s.p = e + 1; return v
    def params(s):
        out = {}
        for _ in range(s.u1()):
            is_str = s.u1() == 1
            k = (s.u1() << 16) | s.u2()
            out[k] = s.string() if is_str else s.i4()
        return out

def decode_osrs_loc(b):
    r = _R(b); d = dict(ops={})
    while True:
        op = r.u1()
        if op == 0: break
        if op in (1, 6):
            n = r.u1(); ms = []
            for _ in range(n):
                m = r.i4() if op == 6 else r.u2()
                ms.append((m, r.u1()))
            if n: d['models'] = ms
        elif op in (5, 7):
            n = r.u1()
            ms = [(r.i4() if op == 7 else r.u2(), 10) for _ in range(n)]
            if n: d['models'] = ms; d['untyped'] = True
        elif op == 2: d['name'] = r.string()
        elif op == 14: d['width'] = r.u1()
        elif op == 15: d['length'] = r.u1()
        elif op == 17: d['blockwalk'] = False; d['blockrange'] = False
        elif op == 18: d['blockrange'] = False
        elif op == 19: d['active'] = r.u1()
        elif op == 21: d['hillskew'] = True
        elif op == 22: d['sharelight'] = True
        elif op == 23: d['occlude'] = True
        elif op == 24:
            a = r.u2(); d['anim'] = None if a == 0xFFFF else a
        elif op == 27: d['interact1'] = True
        elif op == 28: d['wallwidth'] = r.u1()
        elif op == 29: d['ambient'] = r.s1()
        elif op == 39: d['contrast'] = r.s1()
        elif 30 <= op <= 34:
            t = r.string()
            if t.lower() != 'hidden': d['ops'][op - 29] = t
        elif op == 40:
            n = r.u1(); d['recol'] = [(r.u2(), r.u2()) for _ in range(n)]
        elif op == 41:
            n = r.u1(); d['retex'] = [(r.u2(), r.u2()) for _ in range(n)]
        elif op == 61: d['category'] = r.u2()
        elif op == 62: d['mirror'] = True
        elif op == 64: d['shadow'] = False
        elif op == 65: d['resizex'] = r.u2()
        elif op == 66: d['resizey'] = r.u2()
        elif op == 67: d['resizez'] = r.u2()
        elif op == 68: d['mapscene'] = r.u2()
        elif op == 69: d['forceapproach'] = r.u1()
        elif op == 70: d['offsetx'] = r.s2()
        elif op == 71: d['offsety'] = r.s2()
        elif op == 72: d['offsetz'] = r.s2()
        elif op == 73: d['forcedecor'] = True
        elif op == 74: d['breakroutefinding'] = True
        elif op == 75: d['raiseobject'] = r.u1()
        elif op in (77, 92):
            vb = r.u2(); vp = r.u2()
            dflt = r.u2() if op == 92 else None
            n = r.u1()
            ch = [r.u2() for _ in range(n + 1)]
            d['multi'] = dict(varbit=None if vb == 0xFFFF else vb, varp=None if vp == 0xFFFF else vp,
                              children=[None if c == 0xFFFF else c for c in ch],
                              default=None if dflt in (None, 0xFFFF) else dflt)
        elif op == 78: r.u2(); r.u1(); r.u1()
        elif op == 79:
            r.u2(); r.u2(); r.u1(); r.u1()
            n = r.u1(); [r.u2() for _ in range(n)]
        elif op == 81: d['hillskew'] = True; r.u1()
        elif op == 82: d['maparea'] = r.u2()
        elif op in (89, 90, 94): pass
        elif op == 91: r.u1()
        elif op == 93: r.u1(); r.u2(); r.u1(); r.u2()
        elif op == 95: r.u1()
        elif op == 96: r.u1()
        elif op == 100: r.u1(); r.u1(); r.string()
        elif op == 101: r.u1(); r.u2(); r.u2(); r.i4(); r.i4(); r.string()
        elif op == 102: r.u1(); r.u2(); r.u2(); r.u2(); r.i4(); r.i4(); r.string()
        elif op == 249: d['params'] = r.params()
        else:
            raise ValueError(f'unknown loc opcode {op}')
    if r.p != len(b): raise ValueError(f'{len(b) - r.p} leftover bytes')
    return d

def load_osrs_locs(st):
    from reftable import split_group
    rt = st.reftable(2); ids = rt.file_ids[6]
    files = split_group(st.read(2, 6), len(ids))
    out = {}; bad = {}
    for i, f in zip(ids, files):
        if not f: continue
        try: out[i] = decode_osrs_loc(f)
        except Exception as e: bad[i] = str(e)
    return out, bad
