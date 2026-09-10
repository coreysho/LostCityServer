#!/usr/bin/env python3
"""Export a rig (models + converted .anim blobs + seq timing) for offline preview.

Writes nothing into content/ and touches no pack file - this is the "look at it
before you ship it" step, the animation equivalent of ob2render.py.

  python3 tools/models/exportrig474.py <cache> <outdir> --npc 6260 --seq 7059 --seq 7058
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store
from reftable import RefTable, split_group
from animconv474 import (parse_474_frame, parse_474_skeleton, decode_474_seq,
                         emit_377_base, build_377_anim)
from npcconfig474 import load_all as load_npcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache'); ap.add_argument('outdir')
    ap.add_argument('--npc', type=int, required=True)
    ap.add_argument('--seq', action='append', type=int, default=[])
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    st = Store(a.cache)
    rt0 = RefTable(st.read(255, 0)); rt2 = RefTable(st.read(255, 2))

    npc = load_npcs(a.cache)[a.npc]
    print(f'# npc {a.npc}: {npc.get("name")} size={npc.get("size")} models={npc["models"]}')
    for m in npc['models']:
        open(os.path.join(a.outdir, f'model_{m}.ob2'), 'wb').write(st.read(7, m))

    seq_files = split_group(st.read(2, 12), rt2.file_counts[12])
    seqs = {i: b for i, b in zip(rt2.file_ids[12], seq_files) if b}
    want = list(dict.fromkeys(a.seq + [npc[k] for k in ('readyanim', 'walkanim') if k in npc]))
    dec = {s: decode_474_seq(seqs[s]) for s in want if s in seqs}

    groups = sorted({f >> 16 for d in dec.values() for f in d['frames']})
    print(f'# {len(dec)} seq(s) -> frame groups {groups}')

    for g in groups:
        files = split_group(st.read(0, g), rt0.file_counts[g])
        parsed, skels = [], set()
        for fi, blob in zip(rt0.file_ids[g], files):
            if not blob: continue
            sk, n, flags, vals = parse_474_frame(blob)
            skels.add(sk); parsed.append((fi, n, flags, vals))
        assert len(skels) == 1, f'group {g} spans skeletons {skels}'
        sk = skels.pop()
        size, types, counts, labels = parse_474_skeleton(st.read(1, sk))
        base = emit_377_base(size, types, counts, labels)
        blob = build_377_anim(parsed, base)      # frame id = 474 file index, preview only
        open(os.path.join(a.outdir, f'group_{g}.anim'), 'wb').write(blob)
        print(f'#   group {g}: {len(parsed)} frames, skeleton {sk}, '
              f'{len(blob)} bytes -> group_{g}.anim')

    meta = {'npc': a.npc, 'name': npc.get('name'), 'size': npc.get('size'),
            'models': npc['models'], 'recol': npc['recol'],
            'resizeh': npc.get('resizeh'), 'resizev': npc.get('resizev'),
            'seqs': {str(s): {'frames': [[f >> 16, f & 0xffff] for f in d['frames']],
                              'delays': d['delays']} for s, d in dec.items()}}
    json.dump(meta, open(os.path.join(a.outdir, 'rig.json'), 'w'), indent=1)
    print(f'# wrote {a.outdir}/rig.json')


if __name__ == '__main__':
    main()
