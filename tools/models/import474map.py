#!/usr/bin/env python3
"""
Import map squares from the rev 474 (Oct 2007) cache into Lost City .jm2 - first user: the
Construction room templates m29_79 / m30_79, which the 377 content never had.

Why 474 and not OSRS: OSRS rev236 has no m29_79 at all, and 474's terrain and models are already
377-format (claude/cache-import-474.md), so nothing needs re-encoding - only matching and copying.

  * terrain  - 474 m-files are the 377 byte format (opcode 0 end, 1 height, 2-49 overlay+shape,
               50-81 flags, 82+ underlay). Decoded here and written as jm2 MAP lines. The decode must
               consume the file exactly or the square is refused.
  * locs     - 474 l-files are XTEA-encrypted; keys come from the OpenRS2 keys JSON sitting in the
               cache folder (keys-*.json). Each 474 loc id is resolved:
                 REUSE  377 loc with the same id whose display name, size, recolours and model BYTES
                        all match (ids drift between 2006 and 2007, so the id alone proves nothing);
                 REUSE  any other 377 loc with that exact name/size/recolours/model bytes;
                 IMPORT new `loc474_<id>`: 474 model bytes copied (377-format already), recolours
                        baked into the model when RGB15 cannot express them, a .loc config, and
                        loc.pack / model.pack entries.
Multi-locs (varbit transforms) take their default child, as the OSRS importer does.

    python3 tools/models/import474map.py "caches/474 cache" --region 29_79 --region 30_79 \
        --content content --out content/scripts/skill_construction/configs/poh_templates [--dry-run]
"""
import argparse, glob, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store
from reftable import RefTable, split_group
from importosrsmap import container
import osrsmap, jm2
from osrsloc import decode_osrs_loc
from osrslocimport import Content377, SUFFIX, default_child
from importosrs import hsl16_to_rgb15
from osrs2ob2 import parse_ob2, encode as encode_ob2, roundtrip
from animconv474 import pack_append

def jh(n):
    h = 0
    for c in n: h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h

def decode_terrain_377(b):
    """-> {(level, x, z): jm2 tile dict}; raises unless every byte is consumed."""
    p = 0; land = {}
    for lv in range(4):
        for x in range(64):
            for z in range(64):
                d = dict(jm2.EMPTY)
                while True:
                    op = b[p]; p += 1
                    if op == 0: break
                    if op == 1:
                        d['h'] = b[p]; p += 1; break
                    if op <= 49:
                        d['ov'] = b[p]; p += 1; d['shape'] = (op - 2) >> 2; d['rot'] = (op - 2) & 3
                    elif op <= 81: d['flags'] = op - 49
                    else: d['un'] = op - 81
                land[(lv, x, z)] = d
    if p != len(b): raise ValueError(f'terrain walk {p} != {len(b)}')
    return land

class Cache474:
    def __init__(s, path):
        s.st = Store(path)
        rt = RefTable(s.st.read(255, 5), strict=False)
        s.maps = {nh: g for g, nh in rt.group_names.items()}
        kf = [f for f in os.listdir(path) if f.startswith('keys') and f.endswith('.json')]
        if not kf: raise SystemExit(f'no keys-*.json in {path} (OpenRS2 XTEA keys for this cache)')
        s.keys = {r['name']: r for r in json.load(open(os.path.join(path, kf[0])))}
        rt2 = RefTable(s.st.read(255, 2), strict=False)
        ids = rt2.file_ids[6]
        s.locs = {}
        for i, f in zip(ids, split_group(s.st.read(2, 6), len(ids))):
            if not f: continue
            try: s.locs[i] = decode_osrs_loc(f)
            except Exception: pass
    def terrain(s, reg):
        g = s.maps.get(jh('m' + reg))
        if g is None: raise SystemExit(f'no m{reg} in the 474 cache')
        return decode_terrain_377(s.st.read(5, g))
    def locs_of(s, reg):
        k = s.keys.get('l' + reg)
        if k is None: raise SystemExit(f'no XTEA key for l{reg}')
        return osrsmap.decode_locs(container(s.st.raw(5, k['group']), k['key']))
    def model(s, mid):
        return s.st.read(7, mid)

def model_key(files):
    return tuple(sorted(hashlib.sha1(b).hexdigest() for b in files))

class Resolver:
    def __init__(s, c474, c377):
        s.c, s.c3 = c474, c377
        s.by_sig = {}                                  # (name, w, l, recols, model hashes) -> 377 id
        for lid, name in c377.ids.items():
            sig = s.sig377(lid)
            if sig: s.by_sig.setdefault(sig, lid)
    def files377(s, lid):
        name = s.c3.ids.get(lid)
        if name is None or name not in s.c3.cfg: return None
        out = []
        for k, v in s.c3.cfg[name]:
            if not k.startswith('model'): continue
            for sfx in SUFFIX.values():
                p = s.c3.modelfiles.get(v + sfx)
                if p: out.append(open(p, 'rb').read())
            if not any(s.c3.modelfiles.get(v + sfx) for sfx in SUFFIX.values()) and s.c3.modelfiles.get(v):
                out.append(open(s.c3.modelfiles[v], 'rb').read())
        return out
    def sig377(s, lid):
        f = s.files377(lid)
        if not f: return None
        n = s.c3.value(lid, 'name')
        w = int(s.c3.value(lid, 'width') or 1); l = int(s.c3.value(lid, 'length') or 1)
        return (n or None, w, l, tuple(sorted(s.c3.recols(lid))), model_key(f))
    def sig474(s, d):
        f = [s.c.model(m) for m, _ in d.get('models', [])]
        if not f or any(x is None for x in f): return None
        n = d.get('name'); n = None if n in (None, 'null') else n
        return (n, d.get('width', 1), d.get('length', 1), tuple(sorted(d.get('recol') or [])), model_key(f))
    def resolve(s, oid):
        d = s.c.locs.get(oid)
        if d is None: return ('drop', 'no such 474 loc')
        ch = default_child(d, s.c.locs)
        if ch == -1: return ('drop', 'transformer with no default')
        if ch is not None: return s.resolve(ch)
        if not d.get('models'): return ('import', oid)
        if d.get('retex'): return ('import', oid)
        sig = s.sig474(d)
        if sig is None: return ('import', oid)
        if s.sig377(oid) == sig: return ('reuse', oid)
        if sig in s.by_sig: return ('reuse', s.by_sig[sig])
        if s.same_object(oid, d): return ('reuse', oid)
        return ('import', oid)
    def same_object(s, oid, d):
        """Same id, same name/size/recolours/shape set, and at least one model byte-identical: the
        object 377 already has, with a model Jagex touched up in 2007 (desertwall, brickwall and
        yanille_poh_wall all differ by one or two shapes). Keep 377's own art rather than import a
        near-duplicate of a wall that is used all over the world."""
        name = s.c3.ids.get(oid)
        if name is None or name not in s.c3.cfg: return False
        n4 = d.get('name'); n4 = None if n4 in (None, 'null') else n4
        if (s.c3.value(oid, 'name') or None) != n4: return False
        if (int(s.c3.value(oid, 'width') or 1), int(s.c3.value(oid, 'length') or 1)) != (d.get('width', 1), d.get('length', 1)): return False
        if sorted(s.c3.recols(oid)) != sorted(d.get('recol') or []): return False
        base = [v for k, v in s.c3.cfg[name] if k == 'model']
        if len(base) != 1: return False
        same = 0
        for mid, t in d['models']:
            p = s.c3.modelfiles.get(base[0] + SUFFIX[t]) or (s.c3.modelfiles.get(base[0]) if t == 10 else None)
            if p is None: return False
            same += open(p, 'rb').read() == s.c.model(mid)
        return same > 0

def import_loc(c, oid, lines, model_files, notes):
    d = c.locs[oid]
    name = f'loc474_{oid}'
    slots = {}
    for mid, t in d.get('models', []):
        k = 0
        while t in slots.get(k, {}): k += 1
        slots.setdefault(k, {})[t] = mid
    L = [f'[{name}]', f'// rev 474 loc {oid} (import474map.py)']
    if d.get('name') and d['name'] != 'null': L.append(f"name={d['name']}")
    recol_cfg = []; bake = []
    for a, b in d.get('recol') or []:
        ra, oka = hsl16_to_rgb15(a); rb, okb = hsl16_to_rgb15(b)
        if oka and okb: recol_cfg.append((ra, rb))
        else: bake.append((a, b))
    for k in sorted(slots):
        base = name if k == 0 else f'{name}_{k + 1}'
        L.append(('model' if k == 0 else f'model{k + 1}') + f'={base}')
        for t, mid in slots[k].items():
            raw = c.model(mid)
            if raw is None: raise SystemExit(f'loc {oid}: 474 model {mid} missing')
            if raw[-2:] == b'\xff\xff': raise SystemExit(f'loc {oid}: model {mid} is the newer format')
            m = parse_ob2(raw)
            if bake:
                for i in range(m['fcount']):
                    if m['finfo'] and m['finfo'][i] & 2: continue
                    for a, b in bake:
                        if m['colour'][i] == a: m['colour'][i] = b; break
                raw = encode_ob2(m)
                ok, why = roundtrip(raw, m)
                if not ok: raise SystemExit(f'loc {oid} model {mid}: {why}')
            if m['finfo'] and any(f & 2 and m['colour'][i] >= 50 for i, f in enumerate(m['finfo'])):
                notes.append(f'{name}: model {mid} uses a texture id >= 50')
            model_files[base + SUFFIX[t]] = raw
    for i, (a, b) in enumerate(recol_cfg, 1):
        L.append(f'recol{i}s={a}'); L.append(f'recol{i}d={b}')
    for k in ('width', 'length'):
        if d.get(k, 1) != 1: L.append(f'{k}={d[k]}')
    if d.get('blockwalk') is False: L.append('blockwalk=no')
    if d.get('blockrange') is False: L.append('blockrange=no')
    if 'active' in d: L.append('active=' + ('yes' if d['active'] else 'no'))
    for k in ('hillskew', 'sharelight', 'occlude', 'mirror', 'forcedecor', 'breakroutefinding'):
        if d.get(k): L.append(f'{k}=yes')
    if d.get('shadow') is False: L.append('shadow=no')
    for k in ('wallwidth', 'mapscene', 'resizex', 'resizey', 'resizez', 'offsetx', 'offsety', 'offsetz'):
        if k in d: L.append(f'{k}={d[k]}')
    if 'ambient' in d: L.append(f"ambient={d['ambient'] & 0xFF}")
    if 'contrast' in d: L.append(f"contrast={d['contrast'] & 0xFF}")     # 474 lights like 377 (x5)
    if 'raiseobject' in d: L.append('raiseobject=' + ('yes' if d['raiseobject'] else 'no'))
    fa = {0b1110: 'north', 0b1101: 'east', 0b1011: 'south', 0b0111: 'west'}.get((d.get('forceapproach') or 0) & 0xF)
    if fa: L.append(f'forceapproach={fa}')
    for i, t in sorted(d['ops'].items()): L.append(f'op{i}={t}')
    if d.get('anim') is not None: notes.append(f'{name}: 474 anim {d["anim"]} not converted (loc left static)')
    lines.extend(L + [''])
    return name

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache'); ap.add_argument('--region', action='append', required=True)
    ap.add_argument('--content', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    C = a.content
    c = Cache474(a.cache); c3 = Content377(C); R = Resolver(c, c3)
    regions = {r: (c.terrain(r), c.locs_of(r)) for r in a.region}
    used = sorted({l[0] for _, (_, ls) in regions.items() for l in ls})
    plan = {oid: R.resolve(oid) for oid in used}
    kinds = {}
    for v in plan.values(): kinds[v[0]] = kinds.get(v[0], 0) + 1
    print(f'{len(used)} distinct 474 locs: {kinds}')
    lines = ['// Construction room templates imported from the rev 474 cache by tools/models/import474map.py.',
             '// Hotspots ("Chair space", "Door hotspot"...) and the house-style walls 377 never had.', '']
    model_files = {}; notes = []; newname = {}
    for oid, (k, v) in sorted(plan.items()):
        if k == 'import' and v not in newname:
            newname[v] = import_loc(c, v, lines, model_files, notes)
    for n in notes: print('  note:', n)
    print(f'import {len(newname)} locs, {len(model_files)} models; drop {sum(1 for v in plan.values() if v[0] == "drop")}')
    if a.dry_run: return
    locids, _ = pack_append(os.path.join(C, 'pack', 'loc.pack'), [newname[k] for k in sorted(newname)])
    pack_append(os.path.join(C, 'pack', 'model.pack'), sorted(model_files))
    os.makedirs(os.path.join(C, 'models', 'loc'), exist_ok=True)
    for n, b in model_files.items():
        open(os.path.join(C, 'models', 'loc', n + '.ob2'), 'wb').write(b)
    open(a.out + '.loc', 'w', newline='').write('\r\n'.join(lines))
    idmap = {}
    for oid, (k, v) in plan.items():
        if k == 'reuse': idmap[oid] = v
        elif k == 'import': idmap[oid] = locids[newname[v]]
    for reg, (land, ls) in regions.items():
        locs = [(idmap[l[0]], l[1], l[2], l[3], l[4], l[5]) for l in ls if l[0] in idmap]
        path = os.path.join(C, 'maps', f'm{reg}.jm2')
        if os.path.exists(path): raise SystemExit(f'{path} already exists - refusing to overwrite')
        jm2.write(path, land, locs, [], [], nl='\r\n')
        # a map square the build has never had needs its m/l names in the tracked map.pack, or the
        # map packer never looks at the .jm2 (it walks MapPack, not the maps folder)
        ids, _ = pack_append(os.path.join(C, 'pack', 'map.pack'), [f'm{reg}', f'l{reg}'])
        print(f'wrote m{reg}.jm2: {len(locs)} locs ({len(ls) - len(locs)} dropped); map.pack {ids}')

if __name__ == '__main__':
    main()
