#!/usr/bin/env python3
"""
Import items from the rev 474 cache into Lost City content.

474 models are byte-compatible with the 377 client, so models are copied, not converted.
What the cache cannot tell us - wearpos, combat params, weight, examine text - is supplied
in the batch file or added by hand afterwards.

Batch file is TSV, '#' comments allowed:

    474id   local_name        wearpos          model_basename   [desc]
    8844    bronze_defender   lefthand         defender         A bronze defender.
    10551   fighter_torso     torso/arms       fighter_torso    A sturdy torso.
    11665   void_melee_helm   hat/head/jaw     void_helm        A void melee helm.

The wearpos column may name up to THREE slots, slash separated: the slot the item occupies, then
the body parts it HIDES (wearpos2, wearpos3). The cache does not carry these - they are a Lost City
server-side concept - so they have to be supplied here, and getting them wrong means the player's
hair pokes through the helmet or their arms through the sleeves. 377's own conventions:

    hat                 hides nothing - partyhats, face masks that sit on the nose
    hat/head            hoods, coifs, caps            (49 items in all.obj)
    hat/head/jaw        full helms                    (51 items)
    torso/arms          sleeved bodies, platebodies   (117 items)
    torso               chainbodies, sleeveless        (30 items)

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

def model_extent(data):
    """Bounding box of a 377-format .ob2, pure Python. Returns (dx, dy, dz) or None.

    Used to spot FLAT wear models: a frontal face plate is only a couple of units deep and must
    NOT hide the body part behind it, or that part vanishes and the plate floats. The black mask
    (44 x 50 x 2) taught this; a real head covering is 24-38 deep."""
    try:
        b = data
        p = len(b) - 18
        g2 = lambda o: (b[o] << 8) | b[o + 1]
        vcount = g2(p); fcount = g2(p + 2); tcount = b[p + 4]
        f_tex, f_pri, f_alpha, f_flabel, f_vlabel = b[p+5], b[p+6], b[p+7], b[p+8], b[p+9]
        xlen, ylen, zlen, flen = g2(p+10), g2(p+12), g2(p+14), g2(p+16)
        o = vcount + fcount
        if f_pri == 255:  o += fcount
        if f_flabel == 1: o += fcount
        if f_tex == 1:    o += fcount
        if f_vlabel == 1: o += vcount
        if f_alpha == 1:  o += fcount
        o += flen + fcount * 2 + tcount * 6
        xo, yo, zo = o, o + xlen, o + xlen + ylen
        def gsmart(pos):
            return (b[pos] - 64, pos + 1) if b[pos] < 128 else (((b[pos] << 8 | b[pos+1]) - 49152), pos + 2)
        px = py = pz = 0
        xs = ys = zs = []
        mnx = mny = mnz = 1 << 30; mxx = mxy = mxz = -(1 << 30)
        vp, xp, yp, zp = 0, xo, yo, zo
        for _ in range(vcount):
            fl = b[vp]; vp += 1
            dx = dy = dz = 0
            if fl & 1: dx, xp = gsmart(xp)
            if fl & 2: dy, yp = gsmart(yp)
            if fl & 4: dz, zp = gsmart(zp)
            px += dx; py += dy; pz += dz
            mnx = min(mnx, px); mxx = max(mxx, px)
            mny = min(mny, py); mxy = max(mxy, py)
            mnz = min(mnz, pz); mxz = max(mxz, pz)
        return (mxx - mnx, mxy - mny, mxz - mnz)
    except Exception:
        return None


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
        wear = [w.strip() for w in p[2].split('/') if w.strip()]
        if len(wear) > 3:
            raise SystemExit(f'wearpos takes at most 3 slash-separated slots: {ln!r}')
        rows.append({'id': int(p[0]), 'name': p[1], 'wearpos': wear, 'base': p[3],
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
            if key in ('manwear', 'womanwear') and 'head' in r['wearpos']:
                ext = model_extent(st.read(7, mid))
                if ext and min(ext) <= 4:
                    warnings.append(f'{r["name"]}: {key} model {mid} is FLAT ({ext[0]}x{ext[1]}x'
                                    f'{ext[2]}) but wearpos hides "head". A flat face plate needs '
                                    f'the head visible behind it - hiding it deletes the head. '
                                    f'Use hat/jaw instead (cf. slayer_facemask).')
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
        for wi, w in enumerate(r['wearpos']):
            lines.append(f'wearpos{"" if wi == 0 else wi + 1}={w}')
        if o.get('cost') is not None: lines.append(f'cost={o["cost"]}')
        if o.get('members'): lines.append('members=yes')
        if o.get('stackable'): lines.append('stackable=yes')
        if not o.get('tradeable'): lines.append('tradeable=no')
        lines.append('// TODO by hand: weight, category, param= combat bonuses, equip requirement')
        if len(r['wearpos']) == 1 and r['wearpos'][0] in ('hat', 'torso'):
            warnings.append(f'{r["name"]}: wearpos is bare "{r["wearpos"][0]}" - it will hide '
                            f'nothing. Full helms want hat/head/jaw, hoods hat/head, '
                            f'sleeved bodies torso/arms. Verify this is intentional.')
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
