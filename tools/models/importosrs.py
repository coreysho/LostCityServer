#!/usr/bin/env python3
"""Import items from a modern OSRS cache into this 377 build.

Differs from import474.py in two ways that matter:
  * models are RE-ENCODED (osrs2ob2.py), not copied - OSRS uses model formats the 377
    client cannot read, and every conversion is round-trip verified before it is written;
  * wearpos / wearpos2 / wearpos3 come out of the cache. 474 carried none of these, so
    the first 94 imported items all clipped through the player and had to be fixed by
    hand. OSRS numbers the slots exactly as ObjType.getWearPosId does, so they map 1:1.

  python3 tools/models/importosrs.py <cache> --item "Slayer helmet" --name slayer_helm \
          --dir content/scripts/skill_slayer --dry-run
"""
import sys, os, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
from objconfig474 import load_all
from osrs2ob2 import convert_checked
from animconv474 import pack_append

WEARPOS = ['hat', 'back', 'front', 'righthand', 'torso', 'lefthand', 'arms', 'legs',
           'head', 'hands', 'feet', 'jaw', 'ring', 'quiver']

MODEL_FIELDS = [('model', ''), ('manwear', '_manwear'), ('manwear2', '_manwear2'),
                ('womanwear', '_womanwear'), ('womanwear2', '_womanwear2'),
                ('manhead', '_manhead'), ('womanhead', '_womanhead')]


def rgb15_to_hsl16(v):
    """Mirror of ColorConversion.rgb15toHsl16, used to build the reverse table."""
    r = ((v >> 10) & 0x1F) / 31.0
    g = ((v >> 5) & 0x1F) / 31.0
    b = (v & 0x1F) / 31.0
    mx, mn = max(r, g, b), min(r, g, b)
    h = s = 0.0
    li = (mn + mx) / 2.0
    if mn != mx:
        d = mx - mn
        s = d / (mn + mx) if li < 0.5 else d / (2.0 - mx - mn)
        if mx == r:   h = (g - b) / d
        elif mx == g: h = 2.0 + (b - r) / d
        else:         h = 4.0 + (r - g) / d
    h /= 6.0
    hi = int(h * 256.0)
    si = int(s * 256.0)
    if si < 0: si = 0
    elif si > 255: si = 255
    lo = int(li * 256.0)
    if lo < 0: lo = 0
    elif lo > 255: lo = 255
    if lo > 243:   si >>= 4
    elif lo > 217: si >>= 3
    elif lo > 192: si >>= 2
    elif lo > 179: si >>= 1
    return ((hi & 0xFF) >> 2 << 10) + ((si & 0xFF) >> 5 << 7) + (lo >> 1)


_REV = None
def hsl16_to_rgb15(h):
    """A .obj writes RGB15 and the packer converts; cache recolours are already HSL16."""
    global _REV
    if _REV is None:
        _REV = {}
        for v in range(32768):
            _REV.setdefault(rgb15_to_hsl16(v), []).append(v)
    c = _REV.get(h)
    if c:
        return max(c, key=lambda v: sum(((v >> 10) & 31, (v >> 5) & 31, v & 31))), True
    return h, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache')
    ap.add_argument('--item', action='append', default=[],
                    help='cache item name (or id:<obj id>), optionally name=local_name')
    ap.add_argument('--batch', default=None,
                    help='file of "Cache Name=local_name" lines; # comments allowed')
    ap.add_argument('--dir', required=True, help='content/scripts/<area>; configs/ written under it')
    ap.add_argument('--content', default='content')
    ap.add_argument('--out', default=None, help='.obj file to write (default <dir>/configs/osrs.obj)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    items = list(a.item)
    if a.batch:
        for line in open(a.batch, newline='').read().replace('\r\n', '\n').split('\n'):
            line = line.split('#')[0].strip()
            if line: items.append(line)
    if not items:
        raise SystemExit('nothing to import: pass --item or --batch')

    st = Store(a.cache)
    objs = load_all(a.cache)
    named = {}
    for i, o in objs.items():
        if o.get('name') and o['name'] != 'null':
            named.setdefault(o['name'].lower(), (i, o))

    model_pack = os.path.join(a.content, 'pack', 'model.pack')
    obj_pack = os.path.join(a.content, 'pack', 'obj.pack')
    mdir = os.path.join(a.content, 'models', 'obj')

    lines = ['// Imported from a modern OSRS cache by tools/models/importosrs.py.',
             '// Models are RE-ENCODED from OSRS model format into the 317-family format',
             '// (tools/models/osrs2ob2.py); every one is round-trip verified before writing.',
             '// wearpos/wearpos2/wearpos3 come from the cache - do not hand-edit them.', '']
    to_write = {}          # local model name -> ob2 bytes
    warnings = []

    for spec in items:
        cache_name, _, local = spec.partition('=')
        key = cache_name.lower()
        if key.startswith('id:'):
            # "id:<obj id>=local" picks an exact cache record - needed when two items share a
            # name (the open looting bag is also called "Looting bag").
            iid = int(key[3:])
            if iid not in objs:
                warnings.append(f'{cache_name}: no such obj id'); continue
            o = objs[iid]
        elif key not in named:
            warnings.append(f'{cache_name}: not found in the cache'); continue
        else:
            iid, o = named[key]
        local = local or ''.join(c if c.isalnum() else '_' for c in cache_name.lower()).strip('_')

        models = {}
        bad = False
        for field, suffix in MODEL_FIELDS:
            mid = o.get(field)
            if mid is None: continue
            raw = st.read(7, mid)
            if not raw:
                warnings.append(f'{cache_name}: {field} model {mid} absent'); bad = True; break
            try:
                ob2, m, why = convert_checked(raw)
            except ValueError as e:
                warnings.append(f'{cache_name}: {field} model {mid} - {e}'); bad = True; break
            if ob2 is None:
                warnings.append(f'{cache_name}: {field} model {mid} - {why}'); bad = True; break
            models[field] = (f'obj_{local}{suffix}', ob2, m)
        if bad or 'model' not in models:
            continue

        lines.append(f'[{local}]')
        if o.get('name') and o['name'] != 'null':
            lines.append(f'name={o["name"]}')   # unnamed props (emote-only items) keep the default
        if o.get('desc'): lines.append(f'desc={o["desc"]}')
        lines.append(f'model=obj_{local}')
        if 'manwear' in models:
            lines.append(f'manwear=obj_{local}_manwear,{o.get("manwear_off", 0)}')
        if 'manwear2' in models:   lines.append(f'manwear2=obj_{local}_manwear2')
        if 'womanwear' in models:
            lines.append(f'womanwear=obj_{local}_womanwear,{o.get("womanwear_off", 0)}')
        if 'womanwear2' in models: lines.append(f'womanwear2=obj_{local}_womanwear2')
        if 'manhead' in models:    lines.append(f'manhead=obj_{local}_manhead')
        if 'womanhead' in models:  lines.append(f'womanhead=obj_{local}_womanhead')
        for k in ('wearpos', 'wearpos2', 'wearpos3'):
            v = o.get(k)
            if v is not None and 0 <= v < len(WEARPOS):
                lines.append(f'{k}={WEARPOS[v]}')
        # Lost City's obj packer spells these 2dzoom/2dxan/... - the decoder's
        # zoom2d/xan2d names are rejected with "Invalid property key".
        for cfg, k in (('2dzoom', 'zoom2d'), ('2dxan', 'xan2d'), ('2dyan', 'yan2d'),
                       ('2dzan', 'zan2d'), ('2dxof', 'xof2d'), ('2dyof', 'yof2d')):
            if o.get(k) is not None: lines.append(f'{cfg}={o[k]}')
        for n, (src, dst) in enumerate(o.get('recol') or [], start=1):
            sv, ok1 = hsl16_to_rgb15(src)
            dv, ok2 = hsl16_to_rgb15(dst)
            if not (ok1 and ok2):
                warnings.append(f'{cache_name}: recolour {src}->{dst} has no RGB15 preimage')
            lines.append(f'recol{n}s={sv}')
            lines.append(f'recol{n}d={dv}')
        if o.get('weight') is not None: lines.append(f'weight={o["weight"]}g')
        if o.get('cost') is not None:   lines.append(f'cost={o["cost"]}')
        if o.get('members'):            lines.append('members=yes')
        if o.get('stackable'):          lines.append('stackable=yes')
        if o.get('tradeable') is None:  lines.append('tradeable=no')
        for k, v in sorted((o.get('ops') or {}).items()):  lines.append(f'op{k+1}={v}')
        for k, v in sorted((o.get('iops') or {}).items()): lines.append(f'iop{k+1}={v}')
        lines.append('// TODO by hand: category, param= combat bonuses, equip requirement')
        lines.append('')
        for name, ob2, m in models.values():
            to_write[name] = ob2
        print(f'{(o.get("name") or local):<24} obj {iid:<6} {len(models)} model(s), '
              f'{sum(m["vcount"] for _, _, m in models.values())} verts total')

    for w in warnings:
        print(f'  WARNING: {w}')
    text = '\r\n'.join(lines)
    if a.dry_run:
        print('\n' + text); print('# dry run - nothing written'); return

    assigned, _ = pack_append(model_pack, sorted(to_write))
    os.makedirs(mdir, exist_ok=True)
    for name, ob2 in to_write.items():
        open(os.path.join(mdir, f'{name}.ob2'), 'wb').write(ob2)
    print(f'#   wrote {len(to_write)} models, model.pack ids '
          f'{min(assigned.values())}-{max(assigned.values())}')

    locals_ = [l[1:-1] for l in lines if l.startswith('[') and l.endswith(']')]
    obj_assigned, _ = pack_append(obj_pack, locals_)
    print(f'#   obj.pack {min(obj_assigned.values())}-{max(obj_assigned.values())}')

    out = a.out or os.path.join(a.dir, 'configs', 'osrs.obj')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', newline='').write(text)
    print(f'#   wrote {out}')


if __name__ == '__main__':
    main()
