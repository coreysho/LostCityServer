"""Lost City .jm2 map square reader/writer (text). Sections MAP / LOC / NPC / OBJ.
MAP tile: h<height> o<overlay>[;shape;rot] f<flags> u<underlay> (all optional; missing h = perlin)."""
import re
EMPTY = dict(h=None, ov=None, shape=0, rot=0, flags=0, un=0)

def read(path):
    land = {}; locs = []; npcs = []; objs = []; sec = None
    for l in open(path, newline=''):
        l = l.rstrip('\r\n')
        if not l: continue
        if l.startswith('===='): sec = l.strip('= ').strip(); continue
        m = re.match(r'(\d) (\d+) (\d+): ?(.*)', l)
        lv, x, z, rest = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
        if sec == 'MAP':
            d = dict(EMPTY)
            for tok in rest.split():
                k, v = tok[0], tok[1:]
                if k == 'h': d['h'] = int(v)
                elif k == 'o':
                    p = v.split(';'); d['ov'] = int(p[0])
                    if len(p) > 1: d['shape'] = int(p[1])
                    if len(p) > 2: d['rot'] = int(p[2])
                elif k == 'f': d['flags'] = int(v)
                elif k == 'u': d['un'] = int(v)
            land[(lv, x, z)] = d
        elif sec == 'LOC':
            p = [int(v) for v in rest.split()]
            locs.append((p[0], lv, x, z, p[1] if len(p) > 1 else 10, p[2] if len(p) > 2 else 0))
        elif sec == 'NPC':
            npcs.append((int(rest), lv, x, z))
        elif sec == 'OBJ':
            p = rest.split(); objs.append((int(p[0]), int(p[1]), lv, x, z))
    return land, locs, npcs, objs

def tile_text(d):
    out = []
    if d['h'] is not None: out.append(f"h{d['h']}")
    if d['ov'] is not None:
        s = f"o{d['ov']}"
        if d['shape'] or d['rot']:
            s += f";{d['shape']}"
            if d['rot']: s += f";{d['rot']}"
        out.append(s)
    if d['flags']: out.append(f"f{d['flags']}")
    if d['un']: out.append(f"u{d['un']}")
    return ' '.join(out)

def write(path, land, locs, npcs, objs, nl='\n'):
    L = ['==== MAP ====']
    for lv in range(4):
        for x in range(64):
            for z in range(64):
                d = land.get((lv, x, z))
                if d is None: continue
                t = tile_text(d)
                if t: L.append(f'{lv} {x} {z}: {t}')
    L.append(''); L.append('==== LOC ====')
    for (i, lv, x, z, sh, rot) in sorted(locs, key=lambda r: (r[1], r[2], r[3])):
        if sh == 10 and rot == 0: L.append(f'{lv} {x} {z}: {i}')
        elif rot == 0: L.append(f'{lv} {x} {z}: {i} {sh}')
        else: L.append(f'{lv} {x} {z}: {i} {sh} {rot}')
    L.append(''); L.append('==== NPC ====')
    for (i, lv, x, z) in sorted(npcs, key=lambda r: (r[1], r[2], r[3])): L.append(f'{lv} {x} {z}: {i}')
    L.append(''); L.append('==== OBJ ====')
    for (i, c, lv, x, z) in sorted(objs, key=lambda r: (r[2], r[3], r[4])): L.append(f'{lv} {x} {z}: {i} {c}')
    L.append('')
    open(path, 'w', newline='').write(nl.join(L))

def patch_map(path, tiles):
    """Rewrite only the given MAP tiles of an existing .jm2, leaving every other line as it was."""
    raw = open(path, newline='').read(); nl = '\r\n' if '\r\n' in raw else '\n'
    lines = raw.split(nl); out = []; sec = None; done = set()
    for l in lines:
        if l.startswith('===='):
            if sec == 'MAP':
                for (lv, x, z), d in sorted(tiles.items()):
                    if (lv, x, z) not in done and tile_text(d): out.append(f'{lv} {x} {z}: {tile_text(d)}')
            sec = l.strip('= ').strip(); out.append(l); continue
        if sec == 'MAP' and l:
            m = re.match(r'(\d) (\d+) (\d+):', l)
            k = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if k in tiles:
                done.add(k)
                t = tile_text(tiles[k])
                if t: out.append(f'{k[0]} {k[1]} {k[2]}: {t}')
                continue
        out.append(l)
    open(path, 'w', newline='').write(nl.join(out))
