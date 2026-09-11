#!/usr/bin/env python3
"""Re-encode already-imported OSRS loc models in place with the current osrs2ob2.py.

The loc counterpart of reconvert_osrs.py. It touches ONLY the .ob2 bytes: no config is
rewritten, no pack line is added, and it refuses to create a file that does not already
exist, so hand edits to the generated .loc configs are safe.

Which locs to redo comes from pack/model.pack itself - every model the OSRS loc importer
wrote is named osrsloc_<oid>[_<slot>]<shape suffix> - so this needs no batch list and
cannot miss one that was imported by a different run.

  python3 tools/models/reconvert_osrs_locs.py "<osrs cache>" [--content content] [--dry-run]
"""
import sys, os, re, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
from osrsloc import load_osrs_locs
from osrs2ob2 import decode as decode_osrs_model, encode as encode_ob2, roundtrip, SHARED_TEXTURES
from osrslocimport import bake, SUFFIX


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache')
    ap.add_argument('--content', default='content')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    pack = open(os.path.join(a.content, 'pack', 'model.pack'), newline='').read()
    packed = set(re.findall(r'=\s*(osrsloc_\S+)', pack))
    oids = sorted({int(m) for m in re.findall(r'=\s*osrsloc_(\d+)', pack)})
    if not oids:
        raise SystemExit('no osrsloc_* models in model.pack - nothing to do')

    st = Store(a.cache)
    locs = load_osrs_locs(st)
    if isinstance(locs, tuple):
        locs = locs[0]
    mdir = os.path.join(a.content, 'models', 'loc')

    done = changed = 0
    problems = []
    changed_by_loc = collections.Counter()
    for oid in oids:
        d = locs.get(oid)
        if d is None:
            problems.append(f'osrsloc_{oid}: not in this cache'); continue
        # Rebuild the same slot layout import_loc used, so a model lands on the same filename.
        slots = {}
        for mid, t in d.get('models', []):
            k = 0
            while t in slots.get(k, {}):
                k += 1
            slots.setdefault(k, {})[t] = mid
        for k in sorted(slots):
            base = f'osrsloc_{oid}' if k == 0 else f'osrsloc_{oid}_{k + 1}'
            for t, mid in slots[k].items():
                name = base + SUFFIX[t]
                path = os.path.join(mdir, name + '.ob2')
                if name not in packed or not os.path.exists(path):
                    problems.append(f'{name}: not already imported - use importosrsmap.py')
                    continue
                raw = st.read(7, mid)
                if not raw:
                    problems.append(f'{name}: model {mid} absent from the cache'); continue
                m = decode_osrs_model(raw)
                if m is None:
                    problems.append(f'{name}: model {mid} does not decode'); continue
                bake(m, d.get('recol'), d.get('retex'), SHARED_TEXTURES)
                ob2 = encode_ob2(m)
                ok, why = roundtrip(ob2, m)
                if not ok:
                    problems.append(f'{name}: {why}'); continue
                done += 1
                if open(path, 'rb').read() != ob2:
                    changed += 1
                    changed_by_loc[oid] += 1
                    if not a.dry_run:
                        open(path, 'wb').write(ob2)
    print(f'{done} loc models re-encoded, {changed} changed' + (' (dry run)' if a.dry_run else ''))
    for oid, n in changed_by_loc.most_common():
        nm = (locs[oid].get('name') or '?')
        print(f'  loc {oid} ({nm}): {n} model(s)')
    for p in problems:
        print('  PROBLEM:', p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
