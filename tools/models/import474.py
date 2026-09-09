#!/usr/bin/env python3
"""
Import items from the rev 474 cache into Lost City content.

474 models are byte-compatible with the 377 client, so models are copied, not converted.
What the cache cannot tell us - wearpos, combat params, weight, examine text - is supplied
in the batch file or added by hand afterwards.

Batch file is TSV, '#' comments allowed:

    474id   local_name        wearpos     model_basename   [desc]
    8844    bronze_defender   lefthand    defender         A bronze defender.
    8845    iron_defender     lefthand    defender         An iron defender.

model_basename is what makes shared art work: all seven defenders name 'defender', so the
model is imported ONCE as obj_defender and every variant references it with its own recolours.

    python3 import474.py <cache_dir> <batch.tsv> --dry-run     # print configs, touch nothing
    python3 import474.py <cache_dir> <batch.tsv> --content ../../content
"""
import argparse, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store
from objconfig474 import load_all
from ob2palette import REV, TABLE            # RGB15 <-> HSL16, verified against vanilla configs

MODEL_SLOTS = [('model', ''), ('manwear', '_manwear'), ('womanwear', '_womanwear'),
               ('manhead', '_manhead'), ('womanhead', '_womanhead'),
               ('manwear2', '_manwear2'), ('womanwear2', '_womanwear2')]

def hsl16_to_rgb15(h):
    """A .obj config writes RGB15; the packer converts to HSL16. Cache recolours are already
    HSL16, so go back. Values < 100 are passed through raw by ObjConfig.ts, so they are safe
    to emit directly when no preimage exists."""
    c = REV.get(h)
    if c:
        return max(c, key=lambda v: sum(((v >> 10) & 31, (v >> 5) & 31, v & 31))), True
    return h, False

def read_batch(path):
    rows = []
    for ln in open(path, encoding='utf-8'):
        ln = ln.split('#')[0].strip()
        if not ln: continue
        p = [x.strip() for x in ln.split('\t') if x.strip() != '']
        if len(p) < 4:
            raise SystemExit(f'batch line needs at least 4 tab-separated fields: {ln!r}')
        rows.append({'id': int(p[0]), 'name': p[1], 'wearpos': p[2], 'base': p[3],
                     'desc': p[4] if len(p) > 4 else None})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache'); ap.add_argument('batch')
    ap.add_argument('--content', default=None, help='content/ root; omit for --dry-run')
    ap.add_argument('--out', default=None, help='.obj file to write (default: stdout)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    st = Store(a.cache)
    objs = load_all(a.cache)
    rows = read_batch(a.batch)

    model_names = {}          # 474 model id -> local model name
    to_copy = {}              # local model name -> 474 model id
    blocks, warnings = [], []

    for r in rows:
        o = objs.get(r['id'])
        if not o or not o.get('name'):
            warnings.append(f'{r["id"]}: not found in cache or has no name'); continue

        lines = [f'[{r["name"]}]', f'name={o["name"]}']
        if r['desc']: lines.append(f'desc={r["desc"]}')
        elif o.get('desc'): lines.append(f'desc={o["desc"]}')

        for key, suffix in MODEL_SLOTS:
            mid = o.get(key)
            if mid is None: continue
            local = model_names.get(mid)
            if local is None:
                local = f'obj_{r["base"]}{suffix}'
                if local in to_copy and to_copy[local] != mid:
                    local = f'obj_{r["name"]}{suffix}'      # collision: give this one its own
                model_names[mid] = local; to_copy[local] = mid
            if key == 'model':
                lines.append(f'model={local}')
            elif key in ('manwear', 'womanwear'):
                lines.append(f'{key}={local},{o.get(key + "_off", 0)}')
            else:
                lines.append(f'{key}={local}')

        for i, (cfg, src) in enumerate([('2dxof','xof2d'),('2dyof','yof2d'),('2dzoom','zoom2d'),
                                        ('2dxan','xan2d'),('2dyan','yan2d'),('2dzan','zan2d')]):
            if src in o: lines.append(f'{cfg}={o[src]}')

        for n, (s_, d_) in enumerate(o.get('recol', []), start=1):
            sv, ok1 = hsl16_to_rgb15(s_); dv, ok2 = hsl16_to_rgb15(d_)
            if not (ok1 and ok2):
                warnings.append(f'{r["name"]}: recol{n} has no RGB15 preimage '
                                f'(src={s_} dst={d_}) - emitted raw, verify in game')
            lines.append(f'recol{n}s={sv}'); lines.append(f'recol{n}d={dv}')

        for idx, txt in sorted(o.get('iops', {}).items()): lines.append(f'iop{idx+1}={txt}')
        for idx, txt in sorted(o.get('ops', {}).items()):  lines.append(f'op{idx+1}={txt}')
        lines.append(f'wearpos={r["wearpos"]}')
        if o.get('cost') is not None: lines.append(f'cost={o["cost"]}')
        if o.get('members'): lines.append('members=yes')
        if o.get('stackable'): lines.append('stackable=yes')
        if not o.get('tradeable'): lines.append('tradeable=no')
        lines.append('// TODO by hand: weight, category, param= combat bonuses, equip requirement')
        blocks.append('\n'.join(lines))

    text = ('// Imported from the rev 474 cache by tools/models/import474.py\n'
            '// Models are copied byte-for-byte; 474 uses the same model format the 377 client reads.\n'
            '// Everything the cache does not carry is marked TODO below.\n\n'
            + '\n\n'.join(blocks) + '\n')

    print(f'# {len(blocks)} item(s), {len(to_copy)} distinct model(s) to import')
    for local, mid in sorted(to_copy.items()): print(f'#   {local:<34} <- 474 model {mid}')
    for w in warnings: print(f'# WARNING {w}')
    print()

    if a.dry_run or not a.content:
        print(text); return

    dst_dir = os.path.join(a.content, 'models', 'obj')
    packf = os.path.join(a.content, 'pack', 'model.pack')
    s = open(packf, newline='').read(); crlf = '\r\n' in s
    plines = s.replace('\r\n', '\n').rstrip('\n').split('\n')
    have = {l.split('=', 1)[1] for l in plines if '=' in l}
    nxt = max(int(l.split('=', 1)[0]) for l in plines if '=' in l) + 1
    for local, mid in sorted(to_copy.items()):
        d = st.read(7, mid)
        if d[-1] == 0xFF and d[-2] == 0xFF:
            print(f'# SKIP {local}: 474 model {mid} is new-format, needs conversion'); continue
        open(os.path.join(dst_dir, local + '.ob2'), 'wb').write(d)
        if local not in have:
            plines.append(f'{nxt}={local}'); print(f'#   model.pack {nxt}={local}'); nxt += 1
    out = '\n'.join(plines) + '\n'
    open(packf, 'w', newline='').write(out.replace('\n', '\r\n') if crlf else out)

    objpack = os.path.join(a.content, 'pack', 'obj.pack')
    s = open(objpack, newline='').read(); ocrlf = '\r\n' in s
    olines = s.replace('\r\n', '\n').rstrip('\n').split('\n')
    onext = max(int(l.split('=', 1)[0]) for l in olines if '=' in l) + 1
    ohave = {l.split('=', 1)[1] for l in olines if '=' in l}
    for r in rows:
        if r['name'] in ohave: continue
        olines.append(f'{onext}={r["name"]}'); print(f'#   obj.pack {onext}={r["name"]}'); onext += 1
    out = '\n'.join(olines) + '\n'
    open(objpack, 'w', newline='').write(out.replace('\n', '\r\n') if ocrlf else out)

    if a.out:
        open(a.out, 'w', newline='').write(text.replace('\n', '\r\n'))
        print(f'#   wrote {a.out}')

if __name__ == '__main__':
    main()
