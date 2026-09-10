#!/usr/bin/env python3
"""Reader for a `.flatcache` cache dump - one text file per index.

Layout is line-oriented `key=value`, one header then a block per group:

    protocol=7 / revision / compression / crc / named      <- header, once
    id=<group> / namehash / revision / crc
    contents=<base64 of the ordinary cache container>
    compression=<n>
    file=<file id>=<namehash>                              <- one per file in the group

`contents` decodes to exactly the container the packed store holds, so dat2ext's
decompress() handles it unchanged. The `file=` lines carry what a idx255 reference
table would, so this layout needs no reference table at all - which is why this
exposes a RefTable-shaped view of its own.

Group offsets are indexed on first touch rather than decoded eagerly; the model
index runs to ~90MB of text and almost every job wants a handful of groups from it.
"""
import base64, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2ext import decompress


class _Table:
    """Same surface as reftable.RefTable, built from the `file=` lines."""
    def __init__(s, group_ids, file_ids):
        s.protocol = 7
        s.group_ids = group_ids
        s.file_ids = file_ids
        s.file_counts = {g: len(v) for g, v in file_ids.items()}
        s.group_names = {}
        s.file_names = {}

    def group_by_name(s, name):
        return None


class Store:
    def __init__(s, folder):
        s.folder = folder
        s.paths = {int(f.split('.')[0]): os.path.join(folder, f)
                   for f in os.listdir(folder) if f.endswith('.flatcache')}
        s.indices = sorted(s.paths)
        s._scanned = {}
        s._open = {}

    def _scan(s, i):
        if i in s._scanned: return s._scanned[i]
        offsets, files, order = {}, {}, []
        gid = None
        with open(s.paths[i], 'rb') as fh:
            pos = 0
            for line in fh:
                if line.startswith(b'id='):
                    gid = int(line[3:])
                    order.append(gid); files[gid] = []
                elif line.startswith(b'contents='):
                    offsets[gid] = (pos + 9, len(line) - 9)
                elif line.startswith(b'file='):
                    # file=<id>=<namehash>
                    files[gid].append(int(line[5:].split(b'=')[0]))
                pos += len(line)
        s._scanned[i] = (offsets, files, order)
        return s._scanned[i]

    def reftable(s, i):
        offsets, files, order = s._scan(i)
        return _Table(order, files)

    def groups(s, i):
        return s._scan(i)[2]

    def count(s, i):
        return len(s.groups(i))

    def _handle(s, i):
        # one open handle per index - reopening a 90MB file per model turned a
        # whole-index pass from seconds into many minutes
        if i not in s._open:
            s._open[i] = open(s.paths[i], 'rb')
        return s._open[i]

    def raw(s, i, gid):
        offsets, _, _ = s._scan(i)
        if gid not in offsets: return None
        off, n = offsets[gid]
        fh = s._handle(i)
        fh.seek(off)
        return base64.b64decode(fh.read(n).strip())

    def read(s, i, gid):
        d = s.raw(i, gid)
        return None if d is None else decompress(d)


if __name__ == '__main__':
    st = Store(sys.argv[1])
    print('indices:', st.indices)
    for i in st.indices:
        rt = st.reftable(i)
        print(f'  idx{i:<4} groups={len(rt.group_ids):<7} files={sum(rt.file_counts.values())}')
