#!/usr/bin/env python3
"""Solve unknown obj-config opcode payload widths by search.

Method: hold the well-known opcodes fixed, treat the rest as unknown, and repeatedly
take the opcode that is blocking the most records and try every candidate payload
shape, keeping whichever maximises records that decode with ZERO leftover bytes.
Guessing from memory has been wrong three times this project; requiring the whole
record to reconcile is not guessable.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objconfig474 import open_cache
from reftable import split_group

FIXED = {
    1:('g2',), 4:('g2',), 5:('g2',), 6:('g2',), 7:('g2',), 8:('g2',),
    11:('flag',), 12:('g4',), 16:('flag',), 24:('g2',), 26:('g2',),
    65:('flag',), 78:('g2',), 79:('g2',), 90:('g2',), 91:('g2',), 92:('g2',),
    93:('g2',), 94:('g2',), 95:('g2',), 97:('g2',), 98:('g2',),
    110:('g2',), 111:('g2',), 112:('g2',), 113:('g1',), 114:('g1',), 115:('g1',),
    139:('g2',), 140:('g2',), 148:('g2',), 149:('g2',),
    # read out of the bytes directly: 2c 00000a23 | 07 fffc | 08 000c | 04 06f4
    44:('g4',), 75:('g2',), 3:('str',),
}
CANDIDATES = [('flag',), ('g1',), ('g2',), ('g3',), ('g4',),
              ('str',), ('list1',), ('list2',), ('list4',), ('g2g1',)]


def walk(b, table):
    p, n = 0, len(b)
    while p < n:
        op = b[p]; p += 1
        if op == 0: break
        if op == 2 or (30 <= op < 40):
            e = b.find(0, p)
            if e < 0: return 'overrun', op
            p = e + 1; continue
        if op == 23 or op == 25: p += 3; continue
        if op == 40 or op == 41:
            if p >= n: return 'overrun', op
            c = b[p]; p += 1 + 4*c; continue
        if 100 <= op < 110: p += 4; continue
        if op == 249:
            if p >= n: return 'overrun', op
            c = b[p]; p += 1
            for _ in range(c):
                p += 3
                if p >= n: return 'overrun', op
                is_str = b[p]; p += 1
                if is_str == 1:
                    e = b.find(0, p)
                    if e < 0: return 'overrun', op
                    p = e + 1
                else: p += 4
            continue
        shape = table.get(op)
        if shape is None: return 'unknown', op
        k = shape[0]
        if   k == 'flag': pass
        elif k == 'g1':   p += 1
        elif k == 'g2':   p += 2
        elif k == 'g3':   p += 3
        elif k == 'g4':   p += 4
        elif k == 'g2g1': p += 3
        elif k == 'str':
            e = b.find(0, p)
            if e < 0: return 'overrun', op
            p = e + 1
        elif k == 'list1':
            if p >= n: return 'overrun', op
            c = b[p]; p += 1 + c
        elif k == 'list2':
            if p >= n: return 'overrun', op
            c = b[p]; p += 1 + 2*c
        elif k == 'list4':
            if p >= n: return 'overrun', op
            c = b[p]; p += 1 + 4*c
        if p > n: return 'overrun', op
    return ('ok' if p == n else 'tail'), None


def score(records, table):
    ok = 0; blockers = collections.Counter()
    for b in records:
        st, op = walk(b, table)
        if st == 'ok': ok += 1
        elif op is not None: blockers[op] += 1
    return ok, blockers


def main():
    cache = sys.argv[1]
    group = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    st, rt = open_cache(cache)
    records = [b for b in split_group(st.read(2, group), rt.file_counts[group]) if b]
    print(f'group {group}: {len(records)} records')

    table = dict(FIXED)
    for it in range(30):
        ok, blockers = score(records, table)
        print(f'  pass {it}: {ok}/{len(records)} reconcile exactly'
              + (f'   top blocker op {blockers.most_common(1)[0][0]} '
                 f'({blockers.most_common(1)[0][1]} records)' if blockers else ''))
        if not blockers: break
        op = blockers.most_common(1)[0][0]
        best, best_ok = None, ok
        for cand in CANDIDATES:
            t = dict(table); t[op] = cand
            o, _ = score(records, t)
            if o > best_ok: best_ok, best = o, cand
        if best is None:
            print(f'  no candidate shape improves op {op}; stopping'); break
        table[op] = best
        print(f'     -> op {op} = {best[0]}  ({best_ok} reconcile)')

    print('\nsolved opcode table (non-fixed entries):')
    for op in sorted(k for k in table if k not in FIXED):
        print(f'   {op:>3} = {table[op][0]}')


if __name__ == '__main__':
    main()
