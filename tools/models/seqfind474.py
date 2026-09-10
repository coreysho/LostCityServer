#!/usr/bin/env python3
"""Find every 474 seq that animates a given rig.

Give it seq ids you already know (e.g. an npc's readyanim/walkanim); it works out
which frame group(s) those sit on and lists every other seq using the same group.
That is how you recover a boss's whole animation set - attack, death, special -
none of which the npc config carries.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store
from reftable import RefTable, split_group
from animconv474 import decode_474_seq

def main():
    cache = sys.argv[1]
    known = [int(x) for x in sys.argv[2:]]
    st = Store(cache)
    rt2 = RefTable(st.read(255, 2))
    files = split_group(st.read(2, 12), rt2.file_counts[12])
    seqs = {i: b for i, b in zip(rt2.file_ids[12], files) if b}

    # Never swallow a decode failure here. An empty result from this tool reads as
    # "the cache does not have that animation", and that conclusion has been wrong
    # twice now - once from opcode 65 in obj configs, once from 474 seq opcodes not
    # being in ascending order, which hid the frame list of 4,052 of 7,297 seqs.
    dec, failed, noframes = {}, 0, 0
    for i, b in seqs.items():
        try: d = decode_474_seq(b)
        except Exception: failed += 1; continue
        if d.get('_unknown_op'): failed += 1; continue
        if d.get('frames'): dec[i] = d
        else: noframes += 1
    print(f'# {len(dec)}/{len(seqs)} seqs decoded with frames'
          + (f'  ({failed} FAILED, {noframes} had none)' if failed or noframes else ''))
    if failed:
        raise SystemExit('# refusing to search on a partial seq table - fix the decoder first')

    want = set()
    for k in known:
        if k not in dec: print(f'seq {k}: no frame block'); continue
        want |= {f >> 16 for f in dec[k]['frames']}
    print(f'# rig frame group(s): {sorted(want)}')

    hits = [(i, d) for i, d in sorted(dec.items()) if {f >> 16 for f in d['frames']} & want]
    print(f'# {len(hits)} seq(s) share that rig\n')
    for i, d in hits:
        groups = sorted({f >> 16 for f in d['frames']})
        mark = ' <-- given' if i in known else ''
        # priority is the cache telling you what the seq is for: the repo uses 6 for
        # attack and 10 for death, and 474 uses exactly the same convention.
        flags = ' '.join(f'{k}={d[k]}' for k in ('priority', 'maxloops', 'loops') if k in d)
        extra = ' walkmerge' if d.get('walkmerge') else ''
        print(f'  seq {i:<6} frames={len(d["frames"]):<4} lastdelay={d["delays"][-1]:<5}'
              f'{flags}{extra} groups={groups}{mark}')

if __name__ == '__main__':
    main()
