#!/usr/bin/env python3
"""Reader for the .dat2 / idxN file store (RS2 ~rev 400+). 377 uses the older .dat/idx0-4."""
import bz2, gzip, os, sys

SECTOR = 520

class Store:
    def __init__(s, folder):
        s.folder = folder
        s.dat = open(os.path.join(folder, 'main_file_cache.dat2'), 'rb')
        s.idx = {}
        for f in os.listdir(folder):
            if f.startswith('main_file_cache.idx'):
                s.idx[int(f.split('idx')[1])] = open(os.path.join(folder, f), 'rb').read()

    def count(s, i):
        return len(s.idx[i]) // 6

    def raw(s, i, fid):
        ix = s.idx[i]
        off = fid * 6
        if off + 6 > len(ix): return None
        size = int.from_bytes(ix[off:off+3], 'big')
        sec  = int.from_bytes(ix[off+3:off+6], 'big')
        if size <= 0 or sec <= 0: return None
        out = bytearray(); rem = size; chunk = 0
        while rem > 0 and sec > 0:
            s.dat.seek(sec * SECTOR)
            blk = s.dat.read(SECTOR)
            if len(blk) < 8: break
            if fid > 0xFFFF:
                hdr = 10
                cf = int.from_bytes(blk[0:4], 'big'); cc = int.from_bytes(blk[4:6], 'big')
                nxt = int.from_bytes(blk[6:9], 'big'); ci = blk[9]
            else:
                hdr = 8
                cf = int.from_bytes(blk[0:2], 'big'); cc = int.from_bytes(blk[2:4], 'big')
                nxt = int.from_bytes(blk[4:7], 'big'); ci = blk[7]
            if cf != fid or cc != chunk or ci != i:
                raise ValueError(f'sector mismatch idx{i} file{fid}: got file{cf} chunk{cc} idx{ci}')
            n = min(SECTOR - hdr, rem)
            out += blk[hdr:hdr+n]; rem -= n; sec = nxt; chunk += 1
        return bytes(out)

    def read(s, i, fid):
        d = s.raw(i, fid)
        if d is None: return None
        comp = d[0]; clen = int.from_bytes(d[1:5], 'big')
        if comp == 0:
            return d[5:5+clen]
        dlen = int.from_bytes(d[5:9], 'big')
        payload = d[9:9+clen]
        if comp == 1:
            return bz2.decompress(b'BZh1' + payload)[:dlen]
        if comp == 2:
            return gzip.decompress(payload)[:dlen]
        raise ValueError(f'unknown compression {comp}')

if __name__ == '__main__':
    st = Store(sys.argv[1])
    for i in sorted(st.idx):
        print(f'  idx{i:<4} entries={st.count(i)}')
