#!/usr/bin/env python3
"""Compare every OSRS texture against the 50 textures this 377 build ships.

Answers the only question that matters when importing OSRS geometry: can a textured face
keep its texture, or does it have to be painted flat? A face can keep it only when 377 has
the same image, because a 377 model's colour field IS the texture id and the client's
texture table is a hardcoded 50 slots (Pix3D.unpackTextures: `for (i = 0; i < 50; i++)`).
There is no room to add one without a client change and a cache rollout.

The comparison is per-pixel on a 32x32 resample, which separates cleanly: a real match
scores 0.0 and the nearest non-match scores 23+. Nothing lands in between, so there is no
threshold to argue about.

  python3 tools/models/texmatch.py "<osrs cache>" <content dir> [texture ids...]

With no ids it sweeps all of them and prints only the matches, which is how
osrs2ob2.SHARED_TEXTURES was derived.
"""
import sys, os, math, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
from gentexhsl import read_records
import osrssprite
from PIL import Image

N = 32


def osrs_image(st, sprite):
    g = osrssprite.decode(st.read(8, sprite))
    if g is None:
        return None
    s = g['sprites'][0]; pal = g['palette']
    im = Image.new('RGB', (s['w'], s['h']))
    im.putdata([(pal[v] >> 16 & 255, pal[v] >> 8 & 255, pal[v] & 255) for v in s['px']])
    return im.resize((N, N), Image.BILINEAR)


def local_textures(content):
    names = {}
    for line in open(os.path.join(content, 'pack', 'texture.pack')).read().split('\n'):
        if '=' in line:
            i, nm = line.split('=', 1); names[int(i)] = nm.strip()
    ims = {}
    for i, nm in names.items():
        p = os.path.join(content, 'textures', nm + '.png')
        if os.path.exists(p):
            ims[i] = Image.open(p).convert('RGB').resize((N, N), Image.BILINEAR)
    return names, ims


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cache, content = sys.argv[1], sys.argv[2]
    want = [int(x) for x in sys.argv[3:]]
    st = Store(cache)
    names, ims = local_textures(content)
    keys = sorted(ims)
    try:
        import numpy as np
        L = np.stack([np.asarray(ims[k], dtype=np.float32) for k in keys])
    except ImportError:
        L = None
    recs = read_records(st)
    print(f'{len(recs)} OSRS textures vs {len(ims)} local 377 textures')
    matches = 0
    for t, rec in enumerate(recs):
        if want and t not in want:
            continue
        im = osrs_image(st, rec['sprite'])
        if im is None:
            print(f'osrs {t:3d}: sprite {rec["sprite"]} does not decode'); continue
        if L is not None:
            import numpy as np
            a = np.asarray(im, dtype=np.float32)
            d = np.sqrt(((L - a) ** 2).sum(-1)).mean(axis=(1, 2))
            order = sorted(range(len(keys)), key=lambda i: d[i])
            scored = [(float(d[i]), keys[i]) for i in order]
        else:
            pa = list(im.getdata())
            scored = sorted((sum(math.dist(x, y) for x, y in zip(pa, list(ims[k].getdata())))
                             / len(pa), k) for k in keys)
        d0, k0 = scored[0]
        if d0 < 1.0:
            matches += 1
        if want or d0 < 1.0:
            verdict = f'MATCH 377 {k0} ({names[k0]})' if d0 < 1.0 else \
                      f'no match; nearest 377 {k0} ({names[k0]}) at {d0:.1f}'
            print(f'osrs {t:3d} sprite {rec["sprite"]:5d} hsl {rec["hsl"]:5d}: {verdict}')
    if not want:
        print(f'\n{matches} OSRS textures are pixel-identical to a 377 texture; '
              f'the rest must be flattened (osrstexhsl.TEXTURE_HSL gives their colour)')


if __name__ == '__main__':
    main()
