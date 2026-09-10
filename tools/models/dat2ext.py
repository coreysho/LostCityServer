#!/usr/bin/env python3
"""Reader for an *extracted* cache laid out as <index>/<group>.dat.

Same containers and reference tables as the packed .dat2 store, so RefTable and
split_group from reftable.py work unchanged - only the way a group's bytes are
located differs. Exposes the same read()/count() surface as dat2.Store, so every
474 tool can point at either kind of cache.
"""
import bz2, gzip, lzma, os, sys


def decompress(d):
    comp = d[0]; clen = int.from_bytes(d[1:5], 'big')
    if comp == 0:
        return d[5:5+clen]
    dlen = int.from_bytes(d[5:9], 'big')
    payload = d[9:9+clen]
    if comp == 1:
        return bz2.decompress(b'BZh1' + payload)[:dlen]
    if comp == 2:
        return gzip.decompress(payload)[:dlen]
    if comp == 3:
        # LZMA1: the cache stores the 5 props bytes then raw data, with no size field.
        # FORMAT_ALONE wants props + an 8-byte little-endian uncompressed size, so splice
        # the length the container already told us into the header.
        hdr = payload[:5] + dlen.to_bytes(8, 'little')
        return lzma.decompress(hdr + payload[5:], format=lzma.FORMAT_ALONE)[:dlen]
    raise ValueError(f'unknown compression {comp}')


class Store:
    def __init__(s, folder):
        s.folder = folder
        s.indices = sorted(int(d) for d in os.listdir(folder)
                           if d.isdigit() and os.path.isdir(os.path.join(folder, d)))
        s._groups = {}

    def groups(s, i):
        """Group ids present on disk for an index. Cached - these directories are large."""
        if i not in s._groups:
            p = os.path.join(s.folder, str(i))
            s._groups[i] = sorted(int(f[:-4]) for f in os.listdir(p) if f.endswith('.dat'))
        return s._groups[i]

    def count(s, i):
        return len(s.groups(i))

    def raw(s, i, gid):
        p = os.path.join(s.folder, str(i), f'{gid}.dat')
        if not os.path.exists(p): return None
        return open(p, 'rb').read()

    def read(s, i, gid):
        d = s.raw(i, gid)
        return None if d is None else decompress(d)


if __name__ == '__main__':
    st = Store(sys.argv[1])
    print('indices present:', st.indices)
