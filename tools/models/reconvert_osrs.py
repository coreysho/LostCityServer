#!/usr/bin/env python3
"""Re-encode already-imported OSRS item models in place with the current osrs2ob2.py.

Written after the first 192 models shipped without per-face priorities (the torso painted
over the slayer helmet's face) or vertex labels (worn models never moved with the player's
animations). Nothing is registered or renamed: every model already has its model.pack line,
so this only rewrites the .ob2 bytes, and refuses to create a file that does not exist.

  python3 tools/models/reconvert_osrs.py <cache> --batch tools/models/batch_osrs_items.txt \
          --batch tools/models/batch_osrs_outfits.txt [--content content] [--dry-run]
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
from objconfig474 import load_all
from osrs2ob2 import convert_checked
from importosrs import MODEL_FIELDS

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache')
    ap.add_argument('--batch', action='append', default=[])
    ap.add_argument('--content', default='content')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    items = []
    for f in a.batch:
        for line in open(f, newline='').read().replace('\r\n', '\n').split('\n'):
            line = line.split('#')[0].strip()
            if line: items.append(line)
    st = Store(a.cache)
    named = {}
    for i, o in load_all(a.cache).items():
        if o.get('name') and o['name'] != 'null':
            named.setdefault(o['name'].lower(), (i, o))       # same pick as importosrs.py
    packed = set(l.split('=', 1)[1].strip() for l in
                 open(os.path.join(a.content, 'pack', 'model.pack'), newline='').read().splitlines() if '=' in l)
    mdir = os.path.join(a.content, 'models', 'obj')
    done = changed = 0; problems = []
    for spec in items:
        cache_name, _, local = spec.partition('=')
        if cache_name.lower() not in named:
            problems.append(f'{cache_name}: not in cache'); continue
        _, o = named[cache_name.lower()]
        for field, suffix in MODEL_FIELDS:
            mid = o.get(field)
            if mid is None: continue
            name = f'obj_{local}{suffix}'
            path = os.path.join(mdir, name + '.ob2')
            if not os.path.exists(path) or name not in packed:
                problems.append(f'{name}: not already imported - use importosrs.py'); continue
            ob2, m, why = convert_checked(st.read(7, mid))
            if ob2 is None:
                problems.append(f'{name}: {why}'); continue
            old = open(path, 'rb').read()
            done += 1
            if old != ob2:
                changed += 1
                if not a.dry_run: open(path, 'wb').write(ob2)
    print(f'{done} models re-encoded, {changed} changed' + (' (dry run)' if a.dry_run else ''))
    for p in problems: print('  PROBLEM:', p)
    return 1 if problems else 0

if __name__ == '__main__':
    sys.exit(main())
