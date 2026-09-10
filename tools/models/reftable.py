#!/usr/bin/env python3
"""Reference tables (idx255) + group->file splitting for the .dat2 store."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store

class R:
    def __init__(s, b): s.b, s.p = b, 0
    def g1(s):
        v = s.b[s.p]; s.p += 1; return v
    def g2(s):
        v = int.from_bytes(s.b[s.p:s.p+2], 'big'); s.p += 2; return v
    def g4(s):
        v = int.from_bytes(s.b[s.p:s.p+4], 'big'); s.p += 4; return v
    def gsmart(s):
        return s.g2() if s.b[s.p] < 128 else (s.g4() & 0x7fffffff)

def name_hash(n):
    h = 0
    for c in n.upper():
        h = (h * 61 + ord(c) - 32) & 0xffffffff
    return h if h < 0x80000000 else h - 0x100000000

class RefTable:
    """idx255 reference table, protocols 5-7.

    Flag bits (protocol 6+): 1 = name hashes, 2 = whirlpool digests (64 bytes),
    4 = compressed+uncompressed lengths (two ints), 8 = uncompressed checksums (one int).
    474 uses protocol 6 with flags 0; the OSRS cache uses protocol 7 with flags 12/13.
    The parse is checked against the table length - a wrong flag order still yields
    plausible group counts, so anything that does not consume exactly is rejected.
    """
    def __init__(s, data, strict=True):
        r = R(data)
        s.protocol = r.g1()
        s.revision = r.g4() if s.protocol >= 6 else 0
        s.flags = r.g1()
        smart = (lambda: r.gsmart()) if s.protocol >= 7 else (lambda: r.g2())
        n = smart()
        s.group_ids = []
        acc = 0
        for _ in range(n):
            acc += smart()
            s.group_ids.append(acc)
        s.group_names = {}
        if s.flags & 1:
            for g in s.group_ids: s.group_names[g] = r.g4()
        for _ in s.group_ids: r.g4()                       # crcs
        if s.flags & 8:
            for _ in s.group_ids: r.g4()                   # uncompressed crcs
        if s.flags & 2:
            for _ in s.group_ids: r.p += 64                # whirlpool
        if s.flags & 4:
            for _ in s.group_ids: r.g4(); r.g4()           # compressed + uncompressed length
        for _ in s.group_ids: r.g4()                       # versions
        s.file_counts = {}
        for g in s.group_ids:
            s.file_counts[g] = smart()
        s.file_ids = {}
        for g in s.group_ids:
            acc = 0; ids = []
            for _ in range(s.file_counts[g]):
                acc += smart()
                ids.append(acc)
            s.file_ids[g] = ids
        s.file_names = {}
        if s.flags & 1:
            for g in s.group_ids:
                s.file_names[g] = [r.g4() for _ in s.file_ids[g]]
        s.tail = len(data) - r.p
        if strict and s.tail != 0:
            raise ValueError(f'reference table did not consume exactly: {s.tail} bytes left '
                             f'(protocol {s.protocol}, flags {s.flags})')

    def group_by_name(s, name):
        h = name_hash(name) & 0xffffffff
        for g, nh in s.group_names.items():
            if (nh & 0xffffffff) == h: return g
        return None

def split_group(data, count):
    """A group holding >1 file carries per-chunk sizes in a trailer."""
    if count == 1: return [data]
    chunks = data[-1]
    p = len(data) - 1 - chunks * count * 4
    sizes = [[0]*count for _ in range(chunks)]
    r = R(data); r.p = p
    for c in range(chunks):
        acc = 0
        for f in range(count):
            acc += int.from_bytes(r.b[r.p:r.p+4], 'big', signed=True); r.p += 4
            sizes[c][f] = acc
    out = [bytearray() for _ in range(count)]
    off = 0
    for c in range(chunks):
        for f in range(count):
            n = sizes[c][f]
            out[f] += data[off:off+n]; off += n
    return [bytes(x) for x in out]

if __name__ == '__main__':
    st = Store(sys.argv[1])
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    rt = RefTable(st.read(255, idx))
    print(f'idx{idx}: protocol={rt.protocol} revision={rt.revision} flags={rt.flags} groups={len(rt.group_ids)}')
    known = ['obj','npc','loc','seq','spotanim','varbit','inv','idk','flo','flu','enum','struct',
             'param','underlay','overlay','identkit','sequence','varp','varplayer','item','object']
    named = {}
    for k in known:
        g = rt.group_by_name(k)
        if g is not None: named[k] = g
    print('named groups:', named if named else '(no name hashes matched)')
    for g in rt.group_ids:
        print(f'  group {g:<4} files={rt.file_counts[g]:<6} namehash={rt.group_names.get(g)}')
