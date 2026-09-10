#!/usr/bin/env python3
"""Decode 474-era npc configs out of idx2 group 9.

Same discipline as objconfig474.py: an unknown opcode stops the decode and is
recorded, so a mis-read layout shows up as a count instead of as silent garbage.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store
from reftable import RefTable, split_group


class R:
    def __init__(s, b): s.b, s.p = b, 0
    def g1(s):
        v = s.b[s.p]; s.p += 1; return v
    def g1s(s):
        v = s.b[s.p]; s.p += 1; return v - 256 if v > 127 else v
    def g2(s):
        v = int.from_bytes(s.b[s.p:s.p+2], 'big'); s.p += 2; return v
    def g2s(s):
        v = s.g2(); return v - 65536 if v > 32767 else v
    def gstr(s):
        e = s.b.index(0, s.p)
        v = s.b[s.p:e].decode('latin-1'); s.p = e + 1; return v


def decode(b):
    o = {'recol': [], 'models': [], 'heads': []}
    r = R(b)
    while r.p < len(b):
        op = r.g1()
        if op == 0: break
        if op == 1:
            for _ in range(r.g1()): o['models'].append(r.g2())
        elif op == 2:  o['name'] = r.gstr()
        elif op == 12: o['size'] = r.g1()
        elif op == 13: o['readyanim'] = r.g2()
        elif op == 14: o['walkanim'] = r.g2()
        elif op == 15: o['turnleftanim'] = r.g2()
        elif op == 16: o['turnrightanim'] = r.g2()
        elif op == 17:
            o['walkanim'] = r.g2(); o['walkanim_b'] = r.g2()
            o['walkanim_l'] = r.g2(); o['walkanim_r'] = r.g2()
        elif 30 <= op < 35: o.setdefault('ops', {})[op-30] = r.gstr()
        elif op == 40:
            for _ in range(r.g1()): o['recol'].append((r.g2(), r.g2()))
        elif op == 41:
            for _ in range(r.g1()): o.setdefault('retex', []).append((r.g2(), r.g2()))
        elif op == 60:
            for _ in range(r.g1()): o['heads'].append(r.g2())
        elif op == 93: o['minimap'] = 0            # payload-less
        elif op == 95: o['vislevel'] = r.g2()
        elif op == 97: o['resizeh'] = r.g2()
        elif op == 98: o['resizev'] = r.g2()
        elif op == 99: o['renderpriority'] = 1     # payload-less
        elif op == 100: o['ambient'] = r.g1s()
        elif op == 101: o['contrast'] = r.g1s()
        elif op == 102: o['headicon'] = r.g2()
        elif op == 103: o['turnspeed'] = r.g2()
        elif op == 106:
            o['varbit'] = r.g2(); o['varp'] = r.g2()
            o['multinpc'] = [r.g2() for _ in range(r.g1() + 1)]
        elif op == 107: o['active'] = 0            # payload-less (not clickable)
        elif op == 109: o['slowwalk'] = 0          # payload-less
        elif op == 111: o['op111'] = 1             # payload-less
        else:
            o['_unknown_op'] = op; o['_at'] = r.p - 1; break
    o['_tail'] = len(b) - r.p
    return o


def load_all(cache_dir, group=9):
    st = Store(cache_dir)
    rt = RefTable(st.read(255, 2))
    files = split_group(st.read(2, group), rt.file_counts[group])
    out = {}
    for fid, blob in zip(rt.file_ids[group], files):
        if not blob: continue
        try: out[fid] = decode(blob)
        except Exception as e: out[fid] = {'_error': str(e)[:60]}
    return out


def summarise(npcs):
    named = {i: n for i, n in npcs.items() if n.get('name') and n['name'] != 'null'}
    unk = {}
    for n in npcs.values():
        if '_unknown_op' in n: unk[n['_unknown_op']] = unk.get(n['_unknown_op'], 0) + 1
    print(f'decoded {len(npcs)} npcs, {len(named)} named, '
          f'{sum(1 for n in npcs.values() if "_error" in n)} errors, '
          f'{sum(1 for n in npcs.values() if "_unknown_op" in n)} hit an unknown opcode')
    if unk: print('  unknown opcodes:', dict(sorted(unk.items(), key=lambda kv: -kv[1])))
    bad = sum(1 for n in npcs.values() if n.get('_tail', 0) not in (0,))
    print(f'  {bad} did not consume the whole record')
    return named


if __name__ == '__main__':
    npcs = load_all(sys.argv[1])
    named = summarise(npcs)
    for q in sys.argv[2:]:
        print(f'\n--- "{q}" ---')
        for i, n in sorted(named.items()):
            if q.lower() in n['name'].lower():
                print(f'  {i:<6} {n["name"]:<30} lvl={n.get("vislevel"):<5} size={n.get("size")} '
                      f'models={n["models"]} ready={n.get("readyanim")} walk={n.get("walkanim")} '
                      f'recols={len(n["recol"])} ops={list((n.get("ops") or {}).values())}')
