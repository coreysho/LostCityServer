#!/usr/bin/env python3
"""
Import OSRS map squares into the 377 build.

  python3 importosrsmap.py --maps "<rev236 cache folder>" --cache "<newest cache>" \
      --region 44_55 [--region 45_155] --content ../../content \
      --out ../../content/scripts/<area>/configs/<name>     (writes <name>.loc and <name>.seq)

Terrain: OSRS floor ids are the same ids as the 377 build's flo table (checked tile-for-tile: an
unchanged square, m44_56, converts to exactly the existing .jm2), so tiles copy across as they are.
The environment/lighting block newer caches append to terrain files is dropped.

Locs: the OSRS loc file is XTEA-decrypted with the square's key, then every loc id goes through
osrslocimport.resolve() - reuse the 377 loc when it is provably the same object, otherwise import it
as osrsloc_<id>. The square's existing NPC and OBJ spawns are kept.
"""
import argparse, json, os, sys, gzip, bz2, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
import osrsmap, jm2
import osrslocimport as LI
from osrsloc import load_osrs_locs
from animconv474 import pack_append
from animconvosrs import convert_seqs

# OSRS floor ids match the 377 flo table (colours checked one by one for every id the Warriors'
# Guild uses) except where Jagex reused a slot later. Map those onto the 377 floor that looks the same.
#   61: OSRS = hidden overlay (magenta, minimap mud)  377 = desert1 (sand)  -> 42 invisible
OVERLAY_REMAP = {61: 42}

def load_keys(path):
    data = json.load(open(path))
    keys = {}
    if isinstance(data, dict):
        for k, v in data.items(): keys[int(k)] = dict(key=v)
    else:
        for e in data:
            ms = e.get('mapsquare', e.get('region'))
            keys[ms] = dict(key=e.get('key', e.get('keys')), group=e.get('group'), name=e.get('name'))
    return keys

def container(raw, key=None):
    """Decode a cache container, XTEA-decrypting everything after the 5-byte header first."""
    ctype = raw[0]; clen = int.from_bytes(raw[1:5], 'big')
    body = raw[5:]
    if key and any(key):
        # only the container payload is encrypted (clen, +4 for the length word when compressed);
        # anything after it - e.g. the 2-byte version trailer on group files - is not, and a block
        # that straddles it would be decrypted into garbage
        n = clen + (4 if ctype else 0)
        body = osrsmap.xtea_decrypt(body[:n], [k & 0xFFFFFFFF for k in key]) + body[n:]
    if ctype == 0: return body[:clen]
    dlen = int.from_bytes(body[:4], 'big'); payload = body[4:4 + clen]
    if ctype == 1: return bz2.decompress(b'BZh1' + payload)[:dlen]
    if ctype == 2: return gzip.decompress(payload)[:dlen]
    if ctype == 3:
        import lzma
        props = payload[:5]
        d = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[lzma._decode_filter_properties(lzma.FILTER_LZMA1, props)])
        return d.decompress(payload[5:], dlen)
    raise ValueError(f'container type {ctype}')

class MapSource:
    """Map squares from an OpenRS2 flat-file cache (<dir>/cache/<archive>/<group>.dat, groups found
    by name through cache/255/5.dat) or from a .flatcache dump (groups numbered by mapsquare)."""
    def __init__(s, path):
        s.path = path
        s.flat = os.path.isdir(os.path.join(path, 'cache', '5'))
        if s.flat:
            from dat2ext import decompress
            from reftable import RefTable
            rt = RefTable(decompress(open(os.path.join(path, 'cache', '255', '5.dat'), 'rb').read()))
            s.byname = {(nh & 0xFFFFFFFF): g for g, nh in rt.group_names.items()}
        else:
            s.st = Store(path)
        kf = [f for f in os.listdir(path) if f.startswith('keys') and f.endswith('.json')]
        s.keys = load_keys(os.path.join(path, kf[0])) if kf else {}

    @staticmethod
    def _jh(n):
        h = 0
        for c in n: h = (h * 31 + ord(c)) & 0xFFFFFFFF
        return h

    def raw(s, name, ms):
        if s.flat:
            g = s.byname.get(s._jh(name))
            if g is None: return None
            p = os.path.join(s.path, 'cache', '5', f'{g}.dat')
            return open(p, 'rb').read() if os.path.exists(p) else None
        if name[0] == 'm': return s.st.raw(5, ms)
        k = s.keys.get(ms)
        return s.st.raw(5, k['group']) if k and k.get('group') is not None else None

    def terrain(s, reg, ms):
        raw = s.raw(f'm{reg}', ms)
        if raw is None: raise SystemExit(f'no terrain for m{reg} in {s.path}')
        return osrsmap.decode_terrain(container(raw))

    def locs(s, reg, ms):
        k = s.keys.get(ms)
        if k is None: raise SystemExit(f'no XTEA key for m{reg} (mapsquare {ms})')
        raw = s.raw(f'l{reg}', ms)
        if raw is None: raise SystemExit(f'no loc file for l{reg} in {s.path}')
        return osrsmap.decode_locs(container(raw, k['key']))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--maps', required=True); ap.add_argument('--cache', required=True)
    ap.add_argument('--region', action='append', required=True)
    ap.add_argument('--content', required=True); ap.add_argument('--out')
    ap.add_argument('--terrain-only', action='store_true')
    ap.add_argument('--extra-loc', action='append', type=int, default=[],
                    help='OSRS loc id to import even though no map uses it (e.g. the open state of a door)')
    ap.add_argument('--loc-props', help='file of "<osrs loc id> key=value" lines appended to that '
                                        'imported loc (door categories, next_loc_stage, ...)')
    ap.add_argument('--blend', action='append', default=[],
                    help='neighbouring 377 square whose heights within 4 tiles of an imported square '
                         'are taken from OSRS too, so the seam does not step (e.g. 45_55)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    src = MapSource(a.maps); st = Store(a.cache)
    locs, _ = load_osrs_locs(st)
    c377 = LI.Content377(a.content)
    flo_max = max(int(l.split('=')[0]) for l in open(os.path.join(a.content, 'pack', 'flo.pack')) if '=' in l)
    texnames = {}
    for l in open(os.path.join(a.content, 'pack', 'texture.pack')):
        if '=' in l: i, n = l.strip().split('=', 1); texnames[int(i)] = n
    texnames = {i for i in texnames if i in LI.SHARED_TEXTURES}

    to_import = {}; results = {}
    for reg in a.region:
        x0, y0 = map(int, reg.split('_')); ms = (x0 << 8) | y0
        tiles = src.terrain(reg, ms)
        land = {}
        bad_floor = set()
        for lv in range(4):
            for x in range(64):
                for z in range(64):
                    t = dict(tiles[lv][x][z])
                    if t['ov'] in OVERLAY_REMAP: t['ov'] = OVERLAY_REMAP[t['ov']]
                    if t['ov'] is not None and not (0 <= t['ov'] <= flo_max): bad_floor.add(('ov', t['ov']))
                    if t['un'] and t['un'] > flo_max: bad_floor.add(('un', t['un']))
                    land[(lv, x, z)] = t
        if bad_floor: print(f'# m{reg}: floor ids beyond the 377 flo table: {sorted(bad_floor)}')
        placed = []
        if not a.terrain_only:
            placed = src.locs(reg, ms)
            for (oid, lv, x, z, sh, rot) in placed:
                if oid not in results: results[oid] = LI.resolve(st, locs, c377, oid)
        old = os.path.join(a.content, 'maps', f'm{reg}.jm2')
        _, _, npcs, objs = jm2.read(old) if os.path.exists(old) else ({}, [], [], [])
        to_import[reg] = (land, placed, npcs, objs)
        print(f'# m{reg}: {len(placed)} locs placed')

    for oid in a.extra_loc:
        if oid not in results: results[oid] = ('import', oid)
    imp = sorted({r[1] for r in results.values() if r[0] == 'import'})
    reuse = sorted({r[1] for r in results.values() if r[0] == 'reuse'})
    drop = {k: r[1] for k, r in results.items() if r[0] == 'drop'}
    print(f'# loc ids: {len(reuse)} reused as-is, {len(imp)} to import, {len(drop)} dropped {drop}')
    if a.dry_run: return

    lines = ['// OSRS locs imported by tools/models/importosrsmap.py (osrslocimport.py).',
             '// Models re-encoded by osrs2ob2.py with the loc recolours baked in.', '']
    model_files = {}; anim_names = {}
    props = {}
    if a.loc_props:
        for l in open(a.loc_props, newline='').read().replace('\r\n', '\n').split('\n'):
            l = l.split('#')[0].strip()
            if l:
                i, kv = l.split(None, 1); props.setdefault(int(i), []).append(kv)
    for oid in imp:
        LI.import_loc(st, locs, oid, a.content, texnames, anim_names, lines, model_files)
        if oid in props:
            lines.pop()                                  # the blank line import_loc ended with
            lines.extend(props[oid] + [''])
    if imp:
        pack_append(os.path.join(a.content, 'pack', 'loc.pack'), [f'osrsloc_{i}' for i in imp])
        ids, _ = pack_append(os.path.join(a.content, 'pack', 'model.pack'), list(model_files))
        os.makedirs(os.path.join(a.content, 'models', 'loc'), exist_ok=True)
        for n, b in model_files.items():
            open(os.path.join(a.content, 'models', 'loc', n + '.ob2'), 'wb').write(b)
        print(f'# wrote {len(model_files)} loc models')
    locpack = {}
    for l in open(os.path.join(a.content, 'pack', 'loc.pack')):
        if '=' in l: i, n = l.strip().split('=', 1); locpack[n] = int(i)
    def new_id(oid):
        r = results[oid]
        if r[0] == 'reuse': return r[1]
        if r[0] == 'import': return locpack[f'osrsloc_{r[1]}']
        return None
    for reg, (land, placed, npcs, objs) in to_import.items():
        out = []
        for (oid, lv, x, z, sh, rot) in placed:
            nid = new_id(oid)
            if nid is not None: out.append((nid, lv, x, z, sh, rot))
        jm2.write(os.path.join(a.content, 'maps', f'm{reg}.jm2'), land, out, npcs, objs)
        print(f'#   wrote maps/m{reg}.jm2 ({len(out)} locs)')
    for reg in a.blend:
        x0, y0 = map(int, reg.split('_')); ms = (x0 << 8) | y0
        tiles = src.terrain(reg, ms)
        path = os.path.join(a.content, 'maps', f'm{reg}.jm2')
        land, locs3, npcs, objs = jm2.read(path)
        before = {k: dict(v) for k, v in land.items()}
        n = 0
        for imp_reg in a.region:
            ix, iy = map(int, imp_reg.split('_'))
            if abs(ix - x0) + abs(iy - y0) != 1: continue
            for lv in range(4):
                for x in range(64):
                    for z in range(64):
                        near = (ix < x0 and x < 4) or (ix > x0 and x > 59) or (iy < y0 and z < 4) or (iy > y0 and z > 59)
                        if not near: continue
                        t = land.get((lv, x, z), dict(jm2.EMPTY))
                        if t['h'] != tiles[lv][x][z]['h']:
                            t = dict(t); t['h'] = tiles[lv][x][z]['h']; land[(lv, x, z)] = t; n += 1
        jm2.patch_map(path, {k: v for k, v in land.items() if before.get(k) != v})
        print(f'#   m{reg}: {n} seam heights taken from OSRS')
    if a.out:
        if anim_names:
            seq_text = convert_seqs(st, anim_names, a.content)
            open(a.out + '.seq', 'w', newline='').write(seq_text)
        open(a.out + '.loc', 'w', newline='').write('\r\n'.join(lines))
        print(f'#   wrote {a.out}.loc' + (' and .seq' if anim_names else ''))

if __name__ == '__main__':
    main()
