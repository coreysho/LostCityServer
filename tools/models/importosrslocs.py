#!/usr/bin/env python3
"""
Import individual OSRS locs (no map) - models baked with their recolours, config, loc.pack and
model.pack entries - for locs that scripts spawn or swap in rather than ones placed on a map
(importosrsmap.py covers those).

  python3 importosrslocs.py "<newest cache>" --loc 23958 [--loc ...] [--no-anim] \
      [--loc-props props.txt] --content ../../content --out <area>/configs/<name>   (writes <name>.loc)

--no-anim drops the OSRS 'anim=' so the loc is still until a script plays loc_anim on it - an
animated 377 loc loops its seq for ever (e.g. the Warriors' Guild dummies rise once, then stand).
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
from osrsloc import load_osrs_locs
import osrslocimport as LI
from animconv474 import pack_append
from animconvosrs import convert_seqs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache'); ap.add_argument('--loc', action='append', type=int, required=True)
    ap.add_argument('--no-anim', action='store_true')
    ap.add_argument('--loc-props')
    ap.add_argument('--content', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    st = Store(a.cache); locs, _ = load_osrs_locs(st)
    texnames = set()
    for l in open(os.path.join(a.content, 'pack', 'texture.pack')):
        if '=' in l:
            i = int(l.split('=', 1)[0])
            if i in LI.SHARED_TEXTURES: texnames.add(i)
    props = {}
    if a.loc_props:
        for l in open(a.loc_props, newline='').read().replace('\r\n', '\n').split('\n'):
            l = l.split('#')[0].strip()
            if l: i, kv = l.split(None, 1); props.setdefault(int(i), []).append(kv)
    lines = ['// OSRS locs imported by tools/models/importosrslocs.py (osrslocimport.py).',
             '// Models re-encoded by osrs2ob2.py with the loc recolours baked in.', '']
    model_files = {}; anim_names = {}
    for oid in a.loc:
        LI.import_loc(st, locs, oid, a.content, texnames, anim_names, lines, model_files)
        lines.pop()
        if a.no_anim:
            while lines and lines[-1].startswith('anim='): lines.pop()
        lines.extend(props.get(oid, []) + [''])
    if a.no_anim: anim_names = {}
    pack_append(os.path.join(a.content, 'pack', 'loc.pack'), [f'osrsloc_{i}' for i in a.loc])
    ids, _ = pack_append(os.path.join(a.content, 'pack', 'model.pack'), list(model_files))
    os.makedirs(os.path.join(a.content, 'models', 'loc'), exist_ok=True)
    for n, b in model_files.items():
        open(os.path.join(a.content, 'models', 'loc', n + '.ob2'), 'wb').write(b)
    open(a.out + '.loc', 'w', newline='').write('\r\n'.join(lines))
    if anim_names:
        open(a.out + '.seq', 'w', newline='').write(convert_seqs(st, anim_names, a.content))
    print(f'# {len(a.loc)} locs, {len(model_files)} models -> {a.out}.loc' + (' (+ .seq)' if anim_names else ''))

if __name__ == '__main__':
    main()
