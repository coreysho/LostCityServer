#!/usr/bin/env python3
"""Identify a cache and say whether its assets can be imported into this 377 build.

Run this BEFORE spending time (or upload bandwidth) on a cache. It works out the
store layout, parses every reference table, samples each index to see what it
actually holds, and finishes with a verdict on the only question that matters:
do the models parse as the 317-family format the 377 client reads?

  python3 tools/models/cacheid.py "caches/rev 474 cache oct 2007"
  python3 tools/models/cacheid.py "caches/most updated cache"
"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reftable import RefTable


def open_store(folder):
    """Packed (.dat2 + main_file_cache.idxN) or extracted (<index>/<group>.dat)."""
    if os.path.exists(os.path.join(folder, 'main_file_cache.dat2')):
        from dat2 import Store
        return Store(folder), 'packed .dat2 store'
    if os.path.exists(os.path.join(folder, 'main_file_cache.dat')):
        return None, 'old .dat/.idx store (377-era) - not handled by this tool'
    from dat2ext import Store
    return Store(folder), 'extracted <index>/<group>.dat'


def parses_as_377(b):
    """The section-walk reconciliation. A wrong guess still yields plausible counts,
    so the walk has to land exactly on the 18-byte trailer."""
    if len(b) < 18: return 'too small'
    if b[-2:] == b'\xff\xff': return 'newer model format'
    h = len(b) - 18
    g2 = lambda o: (b[o] << 8) | b[o+1]
    vc, fc, tc = g2(h), g2(h+2), b[h+4]
    f_tex, f_pri, f_alpha, f_flabel, f_vlabel = b[h+5], b[h+6], b[h+7], b[h+8], b[h+9]
    xlen, ylen, zlen, flen = g2(h+10), g2(h+12), g2(h+14), g2(h+16)
    o = vc + fc
    if f_pri == 255:  o += fc
    if f_flabel == 1: o += fc
    if f_tex == 1:    o += fc
    if f_vlabel == 1: o += vc
    if f_alpha == 1:  o += fc
    o += flen + fc*2 + tc*6 + xlen + ylen + zlen
    return 'ok' if o == h else 'not this format'


def sniff(b):
    if not b: return 'empty'
    head = b[:32]                      # magic is not always at offset 0 in these containers
    if b'OggS' in head: return 'Ogg audio'
    if b'DDS ' in head: return 'DDS texture (RS3/NXT)'
    if b'RIFF' in head: return 'RIFF audio'
    if b'\x89PNG' in head: return 'PNG'
    if b'JASC' in head or b'KTX' in head: return 'texture'
    if parses_as_377(b) == 'ok': return '377-format model'
    if b[-2:] == b'\xff\xff': return 'newer-format model'
    return None


def main():
    folder = sys.argv[1]
    st, layout = open_store(folder)
    print(f'cache : {folder}')
    print(f'layout: {layout}')
    if st is None: return

    indices = st.indices if hasattr(st, 'indices') else sorted(st.idx)
    tables = {}
    for i in indices:
        if i == 255: continue
        try: raw = st.read(255, i)
        except Exception: continue
        if not raw: continue
        try: tables[i] = RefTable(raw)
        except Exception as e:
            print(f'  idx{i}: reference table would not parse - {str(e)[:60]}')
    protos = collections.Counter(t.protocol for t in tables.values())
    print(f'indices: {len(tables)}   reference-table protocol(s): {dict(protos)}')
    print()

    model_idx, model_rate = None, 0.0
    print(f'{"idx":<6}{"groups":>8}{"files":>10}  content')
    for i, rt in sorted(tables.items()):
        gids = rt.group_ids
        seen = collections.Counter()
        step = max(1, len(gids) // 40)
        n = 0
        for g in gids[::step][:40]:
            try: b = st.read(i, g)
            except Exception: continue
            if not b: continue
            n += 1
            seen[sniff(b) or 'other'] += 1
        top = seen.most_common(1)[0] if seen else ('?', 0)
        rate = top[1] / n if n else 0
        label = f'{top[0]}' + (f' ({rate:.0%} of {n} sampled)' if n else '')
        print(f'{i:<6}{len(gids):>8}{sum(rt.file_counts.values()):>10}  {label}')
        if top[0] == '377-format model' and rate > model_rate:
            model_idx, model_rate = i, rate

    print()
    if model_idx is not None:
        print(f'VERDICT: importable. idx{model_idx} holds 317-family models '
              f'({model_rate:.0%} of the sample), which the 377 client reads unchanged.')
    else:
        kinds = set()
        for i, rt in tables.items():
            for g in rt.group_ids[::max(1, len(rt.group_ids)//8)][:8]:
                try: k = sniff(st.read(i, g))
                except Exception: continue
                if k: kinds.add(k)
        rs3 = [k for k in kinds if 'RS3' in k]
        print('VERDICT: NOT importable by this pipeline - no index holds 317-family models.')
        if rs3:
            print('         ' + ', '.join(sorted(rs3)) + ' means this is a RuneScape 3 / NXT cache.')
        print('         The 474 pipeline works because 474 models ARE 377 models. A cache whose')
        print('         models are a different format needs a real geometry converter, and the')
        print('         art would still break the client 4096-vertex / 50-texture limits.')


if __name__ == '__main__':
    main()
