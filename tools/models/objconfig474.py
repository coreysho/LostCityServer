#!/usr/bin/env python3
"""Decode 474-era obj (item) configs out of idx2 group 10."""
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
    def g4(s):
        v = int.from_bytes(s.b[s.p:s.p+4], 'big'); s.p += 4; return v
    def gstr(s):
        e = s.b.index(0, s.p)
        v = s.b[s.p:e].decode('latin-1'); s.p = e + 1; return v

def decode(b):
    o = {'recol': []}
    r = R(b)
    while r.p < len(b):
        op = r.g1()
        if op == 0: break
        if   op == 1:  o['model'] = r.g2()
        elif op == 2:  o['name'] = r.gstr()
        elif op == 3:  o['desc'] = r.gstr()
        elif op == 4:  o['zoom2d'] = r.g2()
        elif op == 5:  o['xan2d'] = r.g2()
        elif op == 6:  o['yan2d'] = r.g2()
        elif op == 7:  o['xof2d'] = r.g2s()
        elif op == 8:  o['yof2d'] = r.g2s()
        elif op == 11: o['stackable'] = 1
        elif op == 12: o['cost'] = r.g4()
        elif op == 16: o['members'] = 1
        elif op == 23: o['manwear'] = r.g2(); o['manwear_off'] = r.g1()
        elif op == 24: o['manwear2'] = r.g2()
        elif op == 25: o['womanwear'] = r.g2(); o['womanwear_off'] = r.g1()
        elif op == 26: o['womanwear2'] = r.g2()
        elif 30 <= op < 35: o.setdefault('ops', {})[op-30] = r.gstr()
        elif 35 <= op < 40: o.setdefault('iops', {})[op-35] = r.gstr()
        elif op == 40:
            n = r.g1()
            for _ in range(n): o['recol'].append((r.g2(), r.g2()))
        elif op == 78: o['manwear3'] = r.g2()
        elif op == 79: o['womanwear3'] = r.g2()
        elif op == 90: o['manhead'] = r.g2()
        elif op == 91: o['womanhead'] = r.g2()
        elif op == 92: o['manhead2'] = r.g2()
        elif op == 93: o['womanhead2'] = r.g2()
        elif op == 95: o['zan2d'] = r.g2()
        elif op == 97: o['certlink'] = r.g2()
        elif op == 98: o['certtemplate'] = r.g2()
        elif 100 <= op < 110:
            o.setdefault('stackids', []).append((r.g2(), r.g2()))
        elif op == 110: o['resizex'] = r.g2()
        elif op == 111: o['resizey'] = r.g2()
        elif op == 112: o['resizez'] = r.g2()
        elif op == 113: o['ambient'] = r.g1s()
        elif op == 114: o['contrast'] = r.g1s()
        elif op == 115: o['team'] = r.g1()
        elif op == 65: o['tradeable'] = 1   # payload-less flag in this era
        else:
            o['_unknown_op'] = op; break
    return o

def load_all(cache_dir, group=10):
    st = Store(cache_dir)
    rt = RefTable(st.read(255, 2))
    data = st.read(2, group)
    files = split_group(data, rt.file_counts[group])
    ids = rt.file_ids[group]
    out = {}
    for fid, blob in zip(ids, files):
        if not blob: continue
        try: out[fid] = decode(blob)
        except Exception as e: out[fid] = {'_error': str(e)[:40]}
    return out

if __name__ == '__main__':
    objs = load_all(sys.argv[1])
    named = {i: o for i, o in objs.items() if o.get('name') and o['name'] != 'null'}
    print(f'decoded {len(objs)} objs, {len(named)} named, '
          f'{sum(1 for o in objs.values() if "_error" in o)} errors, '
          f'{sum(1 for o in objs.values() if "_unknown_op" in o)} hit an unknown opcode')
    for q in sys.argv[2:]:
        print(f'\n--- "{q}" ---')
        for i, o in sorted(named.items()):
            if q.lower() in o['name'].lower():
                print(f'  {i:<6} {o["name"]:<34} model={o.get("model")} '
                      f'manwear={o.get("manwear")} womanwear={o.get("womanwear")} '
                      f'manhead={o.get("manhead")} zoom={o.get("zoom2d")} recols={len(o["recol"])}')
