#!/usr/bin/env python3
"""Work out the OSRS model header layout by reconciliation.

The section *set* is the same family as the 377 format - vertex flags, face types,
labels, priorities, alphas, colours, index data, x/y/z deltas, texture triples - so
the header's counts and lengths fully determine the body size. Sweep the header size
and field order, and keep whatever makes body-length == sum-of-sections for the whole
index. A layout that is merely plausible will not reconcile 60,000 times.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store

# field orders worth trying; each entry is (name, width) read from the header start
ORDERS = {
 'A': [('vc',2),('fc',2),('tc',1),('tex',1),('pri',1),('alpha',1),('flab',1),('vlab',1),
       ('xl',2),('yl',2),('zl',2),('fl',2)],
 'B': [('vc',2),('fc',2),('tc',1),('tex',1),('pri',1),('alpha',1),('flab',1),('vlab',1),
       ('tskin',1),('xl',2),('yl',2),('zl',2),('fl',2)],
 'C': [('vc',2),('fc',2),('tc',1),('tex',1),('pri',1),('alpha',1),('flab',1),('vlab',1),
       ('xl',2),('yl',2),('zl',2),('fl',2),('tl',2)],
}


def parse_header(b, start, order):
    p = start; out = {}
    for name, w in order:
        out[name] = int.from_bytes(b[p:p+w], 'big'); p += w
    return out, p


def expected_body(h):
    vc, fc, tc = h['vc'], h['fc'], h['tc']
    n = vc + fc                      # vertex flags, face index types
    if h['tex'] == 1:  n += fc       # face render types
    if h['pri'] == 255: n += fc      # per-face priority
    if h['alpha'] == 1: n += fc
    if h['flab'] == 1:  n += fc
    if h['vlab'] == 1:  n += vc
    n += fc * 2                      # colours
    n += h['fl']                     # face index data
    n += h['xl'] + h['yl'] + h['zl']
    n += tc * 6                      # simple texture triples
    return n


def main():
    cache = sys.argv[1]
    st = Store(cache)
    gs = st.groups(7)
    step = max(1, len(gs) // 800)
    sample = []
    for g in gs[::step][:800]:
        b = st.read(7, g)
        if b: sample.append(b)
    by_ver = collections.defaultdict(list)
    for b in sample: by_ver[b[-2:].hex()].append(b)
    print({k: len(v) for k, v in by_ver.items()})

    for ver, models in sorted(by_ver.items()):
        print(f'\n=== version marker {ver}  ({len(models)} models) ===')
        best = []
        for oname, order in ORDERS.items():
            hsize = sum(w for _, w in order)
            for extra in range(0, 20):          # unknown trailing header bytes
                H = hsize + extra
                ok = 0
                for b in models:
                    start = len(b) - 2 - H
                    if start < 0: continue
                    try:
                        h, _ = parse_header(b, start, order)
                        if h['vc'] == 0 or h['fc'] == 0: continue
                        if expected_body(h) == start: ok += 1
                    except Exception: pass
                if ok: best.append((ok, oname, H, extra))
        best.sort(reverse=True)
        for ok, oname, H, extra in best[:5]:
            print(f'   order {oname}  header {H} bytes ({extra} trailing)  -> '
                  f'{ok}/{len(models)} reconcile ({ok/len(models):.0%})')
        if not best: print('   nothing reconciled')


if __name__ == '__main__':
    main()
