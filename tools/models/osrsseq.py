#!/usr/bin/env python3
"""OSRS (rev 226+) seq config decoder - RuneLite SequenceLoader with rev226=True.

Opcode 1 is byte-identical to 474's (count, delays, frame lo16, frame hi16), so frames decoded
here feed animconv474's frame/skeleton converters unchanged. Everything else is read only so the
walk reconciles; a record that does not end exactly on its 0 terminator is rejected.
"""
class R:
    def __init__(s, b): s.b = b; s.p = 0
    def u1(s): v = s.b[s.p]; s.p += 1; return v
    def u2(s): v = (s.b[s.p] << 8) | s.b[s.p+1]; s.p += 2; return v
    def i4(s): v = int.from_bytes(s.b[s.p:s.p+4], 'big', signed=True); s.p += 4; return v
    def s1(s): v = s.b[s.p]; s.p += 1; return v - 256 if v > 127 else v
    def string(s):
        e = s.b.index(0, s.p); v = s.b[s.p:e].decode('latin-1'); s.p = e + 1; return v

def _sound(r):
    r.u2(); r.u1(); r.u1(); r.u1(); r.u1()      # id, weight, loops, location, retain

def decode_osrs_seq(b):
    r = R(b); d = {}
    while True:
        op = r.u1()
        if op == 0: break
        if op == 1:
            n = r.u2()
            d['delays'] = [r.u2() for _ in range(n)]
            lo = [r.u2() for _ in range(n)]
            hi = [r.u2() for _ in range(n)]
            d['frames'] = [(h << 16) | l for l, h in zip(lo, hi)]
        elif op == 2: d['loops'] = r.u2()
        elif op == 3:
            n = r.u1(); d['walkmerge'] = [r.u1() for _ in range(n)]
        elif op == 4: d['reachforward'] = True
        elif op == 5: d['priority'] = r.u1()
        elif op == 6: d['replaceheldleft'] = r.u2()
        elif op == 7: d['replaceheldright'] = r.u2()
        elif op == 8: d['maxloops'] = r.u1()
        elif op == 9: d['preanim_move'] = r.u1()
        elif op == 10: d['postanim_move'] = r.u1()
        elif op == 11: d['duplicatebehaviour'] = r.u1()
        elif op == 12:
            n = r.u1(); [r.u2() for _ in range(n)]; [r.u2() for _ in range(n)]
        elif op == 13: d['animmaya'] = r.i4()
        elif op == 14:
            n = r.u2()
            for _ in range(n): r.u2(); _sound(r)
            d['sounds'] = n
        elif op == 15: r.u2(); r.u2()
        elif op == 16: r.s1()
        elif op == 17:
            n = r.u1(); [r.u1() for _ in range(n)]
        elif op == 18: d['debugname'] = r.string()
        elif op == 19: pass
        else:
            raise ValueError(f'unknown seq opcode {op}')
    if r.p != len(b):
        raise ValueError(f'{len(b) - r.p} leftover bytes')
    return d
