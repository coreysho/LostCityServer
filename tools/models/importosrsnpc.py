#!/usr/bin/env python3
"""
Import OSRS npcs: models (recolours/retextures baked in, re-encoded by osrs2ob2), chathead models,
npc.pack/model.pack entries, OSRS animations (via animconvosrs) and a .npc config skeleton.

  python3 importosrsnpc.py "<newest cache>" --batch npcs.txt --content ../../content \
      --out ../../content/scripts/<area>/configs/<name>   (writes <name>.npc, <name>.seq)

Batch lines:  <osrs npc id> <local name> [ready=X] [walk=X] [attack=X] [defend=X] [death=X]
  X = a 377 seq name (used as is), or osrs:<seq id> to convert that OSRS seq (named osrs_seq_<id>).
Combat numbers come from the cache (stats, level); everything else (hunt mode, drops, max hit,
defence bonuses) is for the config author.
"""
import argparse, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
from osrsnpc import load_osrs_npcs
from osrs2ob2 import decode as decode_osrs_model, encode as encode_ob2, roundtrip, SHARED_TEXTURES
from osrslocimport import bake
from animconv474 import pack_append
from animconvosrs import convert_seqs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache'); ap.add_argument('--batch', required=True)
    ap.add_argument('--content', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    st = Store(a.cache); npcs, _ = load_osrs_npcs(st)
    entries = []
    for line in open(a.batch, newline='').read().replace('\r\n', '\n').split('\n'):
        line = line.split('#')[0].strip()
        if not line: continue
        p = line.split(); kv = dict(x.split('=', 1) for x in p[2:])
        entries.append((int(p[0]), p[1], kv))

    model_files = {}; by_hash = {}; seqs = {}
    L = ['// OSRS npcs imported by tools/models/importosrsnpc.py. Models re-encoded by osrs2ob2.py with',
         '// the npc recolours baked in; stats and level from the cache, the rest by hand.', '']
    def model(mid, d, name):
        m = decode_osrs_model(st.read(7, mid))
        if m is None: raise SystemExit(f'{name}: model {mid} does not decode')
        bake(m, d.get('recol'), d.get('retex'), SHARED_TEXTURES)
        ob2 = encode_ob2(m); ok, why = roundtrip(ob2, m)
        if not ok: raise SystemExit(f'{name}: model {mid}: {why}')
        h = hashlib.sha1(ob2).hexdigest()
        if h in by_hash: return by_hash[h]
        by_hash[h] = name; model_files[name] = ob2; return name
    def seq(v):
        if v.startswith('osrs:'):
            sid = int(v[5:]); n = f'osrs_seq_{sid}'; seqs[sid] = n; return n
        return v
    for oid, name, kv in entries:
        d = npcs[oid]
        L.append(f'[{name}]'); L.append(f'// OSRS npc {oid}')
        if d.get('name'): L.append(f"name={d['name']}")
        for k, mid in enumerate(d.get('models') or [], 1):
            L.append(f'model{k}=' + model(mid, d, f'npc_{name}_{k}'))
        for k, mid in enumerate(d.get('heads') or [], 1):
            L.append(f'head{k}=' + model(mid, d, f'npc_{name}_head{k}'))
        if d.get('size', 1) != 1: L.append(f"size={d['size']}")
        if 'ready' in kv: L.append(f"readyanim={seq(kv['ready'])}")
        if 'walk' in kv: L.append(f"walkanim={seq(kv['walk'])}")
        for k in ('resizeh', 'resizev'):
            if k in d and d[k] != 128: L.append(f'{k}={d[k]}')
        for i, t in sorted(d['ops'].items()): L.append(f'op{i}={t}')
        if d.get('level'): L.append(f"vislevel={d['level']}")
        if d.get('minimap') is False: L.append('minimap=no')
        st6 = d['stats']
        if any(v != 1 for v in st6):
            for k, v in zip(('attack', 'defence', 'strength', 'hitpoints', 'ranged', 'magic'), st6):
                L.append(f'{k}={v}')
        for k in ('attack', 'defend', 'death'):
            if k in kv: L.append(f'param={k}_anim,{seq(kv[k])}')
        L.append('')
    print('\n'.join(L))
    if a.dry_run: return
    ids, _ = pack_append(os.path.join(a.content, 'pack', 'model.pack'), list(model_files))
    os.makedirs(os.path.join(a.content, 'models', 'npc'), exist_ok=True)
    for n, b in model_files.items():
        open(os.path.join(a.content, 'models', 'npc', n + '.ob2'), 'wb').write(b)
    pack_append(os.path.join(a.content, 'pack', 'npc.pack'), [e[1] for e in entries])
    if seqs:
        open(a.out + '.seq', 'w', newline='').write(convert_seqs(st, seqs, a.content))
    open(a.out + '.npc', 'w', newline='').write('\r\n'.join(L))
    print(f'# wrote {len(model_files)} models, {a.out}.npc' + (' and .seq' if seqs else ''))

if __name__ == '__main__':
    main()
