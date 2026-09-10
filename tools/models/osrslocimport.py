#!/usr/bin/env python3
"""
Bring OSRS locs (objects) into the 377 build for an imported map square.

For every OSRS loc id the map uses, `resolve()` decides:
  * REUSE  - the 377 loc with the same id is the same object (same name, size and the same model
             geometry for every shape). Loc ids drifted between 2006 and OSRS - about a fifth of the
             ids both caches share now mean something else (377's 1722 is a staircase, OSRS's is a
             door) - so the id alone is never trusted.
  * IMPORT - a new 377 loc `osrsloc_<id>`: models re-encoded by osrs2ob2 with the loc's recolours
             and retextures BAKED IN (a .loc recol goes through RGB15 and cannot hit every HSL16
             value exactly), a .loc config, loc.pack/model.pack entries, and its animation
             converted by animconvosrs.
Multi-locs (varbit/varp transforms) have no 377 varbit to drive them, so the map gets the child
that OSRS shows by default (the declared default, else the first valid child).
"""
import os, sys, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osrs2ob2 import decode as decode_osrs_model, encode as encode_ob2, roundtrip, SHARED_TEXTURES
from animconv474 import pack_append

SUFFIX = {0: '_1', 1: '_2', 2: '_3', 3: '_4', 4: '_q', 9: '_5', 5: '_w', 6: '_r', 7: '_e', 8: '_t',
          10: '_8', 11: '_9', 22: '_0', 12: '_a', 13: '_s', 14: '_d', 15: '_f', 16: '_g', 17: '_h',
          18: '_z', 19: '_x', 20: '_c', 21: '_v'}
SUFFIX_TO_SHAPE = {v: k for k, v in SUFFIX.items()}

def _ob2_counts(path):
    b = open(path, 'rb').read()
    vc = (b[-18] << 8) | b[-17]; fc = (b[-16] << 8) | b[-15]
    return vc, fc

class Content377:
    def __init__(s, C):
        s.C = C
        s.ids = {}
        for l in open(os.path.join(C, 'pack', 'loc.pack')):
            if '=' in l:
                i, n = l.strip().split('=', 1); s.ids[int(i)] = n
        s.cfg = {}
        for f in glob.glob(os.path.join(C, 'scripts', '**', '*.loc'), recursive=True):
            txt = open(f, encoding='latin-1').read().replace('\r', '')
            for blk in ('\n' + txt).split('\n[')[1:]:
                n = blk.split(']')[0]; kv = []
                for line in blk.split('\n')[1:]:
                    if '=' in line and not line.startswith('//'):
                        kv.append(tuple(line.split('=', 1)))
                s.cfg[n] = kv
        s.modelfiles = {os.path.basename(p)[:-4]: p for p in
                        glob.glob(os.path.join(C, 'models', '**', '*.ob2'), recursive=True)}

    def geometry(s, lid):
        """{shape: sorted [(vcount, fcount)]} of a 377 loc, or None"""
        name = s.ids.get(lid)
        if name is None or name not in s.cfg: return None
        out = {}
        for k, v in s.cfg[name]:
            if not k.startswith('model'): continue
            for sfx, shape in SUFFIX_TO_SHAPE.items():
                p = s.modelfiles.get(v + sfx) or (s.modelfiles.get(v) if shape == 10 else None)
                if p: out.setdefault(shape, []).append(_ob2_counts(p))
        return {k: sorted(v) for k, v in out.items()}

    def recols(s, lid):
        """377 recolours as HSL16 pairs (.loc files store RGB15)."""
        from importosrs import rgb15_to_hsl16
        out = []; k = 1
        while s.value(lid, f'recol{k}s') is not None:
            out.append((rgb15_to_hsl16(int(s.value(lid, f'recol{k}s'))),
                        rgb15_to_hsl16(int(s.value(lid, f'recol{k}d')))))
            k += 1
        return out

    def value(s, lid, key):
        name = s.ids.get(lid)
        for k, v in s.cfg.get(name, []):
            if k == key: return v
        return None

def osrs_geometry(st, d):
    out = {}
    for mid, t in d.get('models', []):
        raw = st.read(7, mid)
        if raw is None: return None
        m = decode_osrs_model(raw)
        if m is None: return None
        out.setdefault(t, []).append((m['vcount'], m['fcount']))
    return {k: sorted(v) for k, v in out.items()}

def default_child(d, locs):
    m = d.get('multi')
    if not m: return None
    if m['default'] is not None and m['default'] in locs: return m['default']
    for c in m['children']:
        if c is not None and c in locs and locs[c].get('models'): return c
    return -1          # a transformer with nothing to show by default

def resolve(st, locs, c377, oid):
    """-> ('reuse', 377 id) | ('import', osrs id) | ('drop', reason)"""
    d = locs.get(oid)
    if d is None: return ('drop', 'no such OSRS loc')
    ch = default_child(d, locs)
    if ch == -1: return ('drop', 'transformer with no default')
    if ch is not None: return resolve(st, locs, c377, ch)
    if not d.get('models'): return ('import', oid)          # invisible blockers etc.
    g3 = c377.geometry(oid)
    if g3:
        n3 = c377.value(oid, 'name'); w3 = int(c377.value(oid, 'width') or 1); l3 = int(c377.value(oid, 'length') or 1)
        if (n3 or None) == (d.get('name') if d.get('name') not in (None, 'null') else None) \
                and w3 == d.get('width', 1) and l3 == d.get('length', 1) \
                and g3 == osrs_geometry(st, d) and not d.get('retex') \
                and sorted(c377.recols(oid)) == sorted(d.get('recol') or []):
            return ('reuse', oid)
    return ('import', oid)

def bake(m, recol, retex, texnames):
    """Apply a loc's recolours / retextures to a decoded model in place."""
    fi = m.get('finfo') or [0] * m['fcount']
    for i in range(m['fcount']):
        c = m['colour'][i]
        if fi[i] & 2:                                   # textured: colour is the texture id
            for a, b in retex or []:
                if c == a:
                    if b in texnames: m['colour'][i] = b
                    break
        else:
            for a, b in recol or []:
                if c == a: m['colour'][i] = b; break
    return m

def import_loc(st, locs, oid, C, texnames, anim_names, lines, model_files):
    d = locs[oid]
    name = f'osrsloc_{oid}'
    slots = {}                                          # slot -> {type: model}
    for mid, t in d.get('models', []):
        k = 0
        while t in slots.get(k, {}): k += 1
        slots.setdefault(k, {})[t] = mid
    L = [f'[{name}]', f'// OSRS loc {oid}']
    if d.get('name') and d['name'] != 'null': L.append(f"name={d['name']}")
    for k in sorted(slots):
        base = name if k == 0 else f'{name}_{k + 1}'
        L.append(('model' if k == 0 else f'model{k + 1}') + f'={base}')
        for t, mid in slots[k].items():
            raw = st.read(7, mid)
            m = decode_osrs_model(raw)
            if m is None: raise SystemExit(f'loc {oid}: model {mid} does not decode')
            bake(m, d.get('recol'), d.get('retex'), texnames)
            ob2 = encode_ob2(m)
            ok, why = roundtrip(ob2, m)
            if not ok: raise SystemExit(f'loc {oid} model {mid}: {why}')
            model_files[base + SUFFIX[t]] = ob2
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
    # OSRS lights with contrast*25, the 377 client with contrast*5 (LocType op 39)
    if 'contrast' in d: L.append(f"contrast={max(-128, min(127, d['contrast'] * 5)) & 0xFF}")
    if 'raiseobject' in d: L.append('raiseobject=' + ('yes' if d['raiseobject'] else 'no'))
    fa = {0b1110: 'north', 0b1101: 'east', 0b1011: 'south', 0b0111: 'west'}.get((d.get('forceapproach') or 0) & 0xF)
    if fa: L.append(f'forceapproach={fa}')
    for i, t in sorted(d['ops'].items()): L.append(f'op{i}={t}')
    if d.get('anim') is not None:
        anim_names[d['anim']] = f'osrsloc_anim_{d["anim"]}'
        L.append(f'anim=osrsloc_anim_{d["anim"]}')
    lines.extend(L + [''])
    return name
