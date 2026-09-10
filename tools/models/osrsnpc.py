#!/usr/bin/env python3
"""OSRS npc config decoder - idx2 group 9, RuneLite NpcLoader (rev 233). Rejects records that do not
end exactly on their terminator."""
from osrsloc import _R

def _bigsmart2(r):
    if r.b[r.p] >= 128: return r.i4() & 0x7FFFFFFF
    v = r.u2(); return -1 if v == 32767 else v

def _smart_minus1(r):
    if r.b[r.p] < 128: return r.u1() - 1
    return r.u2() - 32768 - 1

def decode_osrs_npc(b):
    r = _R(b); d = dict(ops={}, stats=[1]*6, size=1)
    while True:
        op = r.u1()
        if op == 0: break
        if op == 1: d['models'] = [r.u2() for _ in range(r.u1())]
        elif op == 61: d['models'] = [r.i4() for _ in range(r.u1())]
        elif op == 2: d['name'] = r.string()
        elif op == 12: d['size'] = r.u1()
        elif op == 13: d['ready'] = r.u2()
        elif op == 14: d['walk'] = r.u2()
        elif op == 15: d['turnleft_idle'] = r.u2()
        elif op == 16: d['turnright_idle'] = r.u2()
        elif op == 17:
            d['walk'] = r.u2(); d['walk_b'] = r.u2(); d['walk_l'] = r.u2(); d['walk_r'] = r.u2()
        elif op == 18: d['category'] = r.u2()
        elif 30 <= op <= 34:
            t = r.string()
            if t.lower() != 'hidden': d['ops'][op - 29] = t
        elif op == 40: d['recol'] = [(r.u2(), r.u2()) for _ in range(r.u1())]
        elif op == 41: d['retex'] = [(r.u2(), r.u2()) for _ in range(r.u1())]
        elif op == 60: d['heads'] = [r.u2() for _ in range(r.u1())]
        elif op == 62: d['heads'] = [r.i4() for _ in range(r.u1())]
        elif 74 <= op <= 79: d['stats'][op - 74] = r.u2()   # attack defence strength hitpoints ranged magic
        elif op == 93: d['minimap'] = False
        elif op == 95: d['level'] = r.u2()
        elif op == 97: d['resizeh'] = r.u2()
        elif op == 98: d['resizev'] = r.u2()
        elif op == 99: d['priority'] = 1
        elif op == 100: d['ambient'] = r.s1()
        elif op == 101: d['contrast'] = r.s1()
        elif op == 102:
            bits = r.u1(); i = 0
            while bits >> i:
                if bits & (1 << i): _bigsmart2(r); _smart_minus1(r)
                i += 1
        elif op == 103: d['turnspeed'] = r.u2()
        elif op in (106, 118):
            vb = r.u2(); vp = r.u2()
            dflt = r.u2() if op == 118 else None
            n = r.u1(); ch = [r.u2() for _ in range(n + 1)]
            d['multi'] = dict(varbit=None if vb == 0xFFFF else vb, varp=None if vp == 0xFFFF else vp,
                              children=[None if c == 0xFFFF else c for c in ch],
                              default=None if dflt in (None, 0xFFFF) else dflt)
        elif op == 107: d['interactable'] = False
        elif op == 109: d['rotflag'] = False
        elif op == 111: d['priority'] = 2
        elif op == 114: d['run'] = r.u2()
        elif op == 115: d['run'] = r.u2(); r.u2(); r.u2(); r.u2()
        elif op == 116: d['crawl'] = r.u2()
        elif op == 117: r.u2(); r.u2(); r.u2(); r.u2()
        elif op in (122, 123, 129, 130, 145, 147): pass
        elif op == 124: d['height'] = r.u2()
        elif op == 126: d['footprint'] = r.u2()
        elif op == 146: r.u2()
        elif op == 249: d['params'] = r.params()
        elif op == 251: r.u1(); r.u1(); r.string()
        elif op == 252: r.u1(); r.u2(); r.u2(); r.i4(); r.i4(); r.string()
        elif op == 253: r.u1(); r.u2(); r.u2(); r.u2(); r.i4(); r.i4(); r.string()
        else: raise ValueError(f'unknown npc opcode {op}')
    if r.p != len(b): raise ValueError(f'{len(b) - r.p} leftover bytes')
    return d

def load_osrs_npcs(st):
    from reftable import split_group
    rt = st.reftable(2); ids = rt.file_ids[9]
    files = split_group(st.read(2, 9), len(ids))
    out = {}; bad = {}
    for i, f in zip(ids, files):
        if not f: continue
        try: out[i] = decode_osrs_npc(f)
        except Exception as e: bad[i] = str(e)
    return out, bad
