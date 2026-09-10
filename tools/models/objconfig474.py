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
    def g3(s):
        v = int.from_bytes(s.b[s.p:s.p+3], 'big'); s.p += 3; return v
    def g4(s):
        v = int.from_bytes(s.b[s.p:s.p+4], 'big'); s.p += 4; return v
    def gstr(s):
        e = s.b.index(0, s.p)
        v = s.b[s.p:e].decode('latin-1'); s.p = e + 1; return v

def decode(b):
    """Decode an obj (item) config. Covers both the 474 era and modern OSRS.

    Opcode set is a superset: 474 never emits 13/44/94/148/249, so one decoder serves
    both caches. Unknown opcodes are recorded and the leftover-byte count is returned,
    because an opcode read at the wrong width silently truncates the rest of the record -
    which is how 3,265 of 474's items once decoded with no name and looked absent.
    """
    o = {'recol': [], 'retex': []}
    r = R(b)
    n = len(b)
    while r.p < n:
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
        elif op == 13: o['wearpos'] = r.g1()          # OSRS: equipment slot
        elif op == 14: o['wearpos2'] = r.g1()         # OSRS: body part to hide
        elif op == 15: o['op15'] = 1                  # OSRS, payload-less
        elif op == 27: o['wearpos3'] = r.g1()         # OSRS: second part to hide
        elif op == 16: o['members'] = 1
        elif op == 23: o['manwear'] = r.g2(); o['manwear_off'] = r.g1()
        elif op == 24: o['manwear2'] = r.g2()
        elif op == 25: o['womanwear'] = r.g2(); o['womanwear_off'] = r.g1()
        elif op == 26: o['womanwear2'] = r.g2()
        elif 30 <= op < 35: o.setdefault('ops', {})[op-30] = r.gstr()
        elif 35 <= op < 40: o.setdefault('iops', {})[op-35] = r.gstr()
        elif op == 40:
            for _ in range(r.g1()): o['recol'].append((r.g2(), r.g2()))
        elif op == 41:
            for _ in range(r.g1()): o['retex'].append((r.g2(), r.g2()))
        elif op == 42: o['shiftclickdrop'] = r.g1s()   # single byte, not a counted list
        elif op == 43: o['op43'] = r.g1s()
        # Modern OSRS moved every model id to a 4-byte opcode in the 44-54 block; ids
        # outgrew 65535 and ops 1/23/24/25/26/78/79/90-93 no longer appear at all.
        elif op == 44: o['model'] = r.g4()
        elif op == 45: o['manwear'] = r.g4(); o['manwear_off'] = r.g1()
        elif op == 46: o['manwear2'] = r.g4()
        elif op == 47: o['manwear3'] = r.g4()
        elif op == 48: o['womanwear'] = r.g4(); o['womanwear_off'] = r.g1()
        elif op == 49: o['womanwear2'] = r.g4()
        elif op == 50: o['womanwear3'] = r.g4()
        elif op == 51: o['manhead'] = r.g4()
        elif op == 52: o['manhead2'] = r.g4()
        elif op == 53: o['womanhead'] = r.g4()
        elif op == 54: o['womanhead2'] = r.g4()
        elif op == 65: o['tradeable'] = 1             # payload-less flag
        elif op == 75: o['weight'] = r.g2()   # grams
        elif op == 78: o['manwear3'] = r.g2()
        elif op == 79: o['womanwear3'] = r.g2()
        elif op == 90: o['manhead'] = r.g2()
        elif op == 91: o['womanhead'] = r.g2()
        elif op == 92: o['manhead2'] = r.g2()
        elif op == 93: o['womanhead2'] = r.g2()
        elif op == 94: o['category'] = r.g2()
        elif op == 95: o['zan2d'] = r.g2()
        elif op == 96: o['dummyitem'] = r.g1()
        elif op == 97: o['certlink'] = r.g2()
        elif op == 98: o['certtemplate'] = r.g2()
        elif 100 <= op < 110: o.setdefault('stackids', []).append((r.g2(), r.g2()))
        elif op == 110: o['resizex'] = r.g2()
        elif op == 111: o['resizey'] = r.g2()
        elif op == 112: o['resizez'] = r.g2()
        elif op == 113: o['ambient'] = r.g1s()
        elif op == 114: o['contrast'] = r.g1s()
        elif op == 115: o['team'] = r.g1()
        elif op == 139: o['boughtlink'] = r.g2()
        elif op == 140: o['boughttemplate'] = r.g2()
        elif op == 148: o['placeholderlink'] = r.g2()
        elif op == 149: o['placeholdertemplate'] = r.g2()
        elif op == 160: o['op160'] = 1                # payload-less
        elif op == 249:
            # isString comes FIRST, then the 3-byte key. The other way round eats the
            # key as a flag and desyncs the rest of the record.
            params = {}
            for _ in range(r.g1()):
                is_str = r.g1()
                key = int.from_bytes(b[r.p:r.p+3], 'big'); r.p += 3
                params[key] = r.gstr() if is_str == 1 else r.g4()
            o['params'] = params
        else:
            o['_unknown_op'] = op; o['_at'] = r.p - 1; break
    o['_tail'] = n - r.p
    return o

def open_cache(cache_dir):
    """Packed .dat2, extracted <index>/<group>.dat, or a .flatcache dump."""
    import glob
    if glob.glob(os.path.join(cache_dir, '*.flatcache')):
        from flatcache import Store as FS
        st = FS(cache_dir)
        return st, st.reftable(2)
    if os.path.exists(os.path.join(cache_dir, 'main_file_cache.dat2')):
        st = Store(cache_dir)
    else:
        from dat2ext import Store as ES
        st = ES(cache_dir)
    return st, RefTable(st.read(255, 2))


def load_all(cache_dir, group=10):
    st, rt = open_cache(cache_dir)
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
