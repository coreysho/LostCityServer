#!/usr/bin/env python3
"""OSRS spotanim (idx2 group 13) decoder. Rejects records that do not end on their terminator."""
def decode_osrs_spot(b):
    p = 0; d = {}
    def u1():
        nonlocal p; v = b[p]; p += 1; return v
    def u2():
        nonlocal p; v = (b[p] << 8) | b[p+1]; p += 2; return v
    while True:
        op = u1()
        if op == 0: break
        if op == 1: d['model'] = u2()
        elif op == 3:                           # newer caches: 32-bit model id
            d['model'] = (u2() << 16) | u2()
        elif op == 2: d['anim'] = u2()
        elif op == 4: d['resizeh'] = u2()
        elif op == 5: d['resizev'] = u2()
        elif op == 6: d['angle'] = u2()
        elif op == 7: d['ambient'] = u1()
        elif op == 8: d['contrast'] = u1()
        elif op == 9: d['op9'] = True
        elif op == 40:
            n = u1(); d['recol'] = [(u2(), u2()) for _ in range(n)]
        elif op == 41:
            n = u1(); d['retex'] = [(u2(), u2()) for _ in range(n)]
        else:
            raise ValueError(f'unknown spotanim opcode {op}')
    if p != len(b): raise ValueError(f'{len(b)-p} leftover bytes')
    return d

def load_osrs_spots(st):
    from reftable import split_group
    rt = st.reftable(2); ids = rt.file_ids[13]
    return {i: f for i, f in zip(ids, split_group(st.read(2, 13), len(ids))) if f}
