#!/usr/bin/env python3
"""OSRS map squares (idx5): terrain ('m') and loc ('l') files - RuneLite MapLoader /
LocationsLoader, current format (u2 terrain opcodes, int-smart loc ids). Loc files are XTEA
encrypted; decrypt with the region key from an OpenRS2 keys.json first."""
import struct

def decode_terrain(b, strict=False):
    """-> tiles[level][x][z] = dict(h, ov, shape, rot, flags, un).

    Recent caches append per-square environment data (lighting / fog floats) after the 4x64x64
    tile walk; it has no 377 equivalent and is ignored unless strict=True."""
    p = 0; n = len(b)
    tiles = [[[None]*64 for _ in range(64)] for _ in range(4)]
    for lv in range(4):
        for x in range(64):
            for z in range(64):
                t = dict(h=None, ov=None, shape=0, rot=0, flags=0, un=0)
                while True:
                    a = (b[p] << 8) | b[p+1]; p += 2
                    if a == 0: break
                    if a == 1:
                        t['h'] = b[p]; p += 1; break
                    if a <= 49:
                        t['ov'] = struct.unpack('>h', b[p:p+2])[0]; p += 2
                        t['shape'] = (a - 2) // 4; t['rot'] = (a - 2) & 3
                    elif a <= 81:
                        t['flags'] = a - 49
                    else:
                        t['un'] = a - 81
                tiles[lv][x][z] = t
    if p > n or (strict and p != n): raise ValueError(f'terrain walk {p} != {n}')
    return tiles

def _smart_s(b, p):              # unsigned short smart
    if b[p] < 128: return b[p], p + 1
    return ((b[p] << 8) | b[p+1]) - 32768, p + 2

def _int_smart_compat(b, p):     # readUnsignedIntSmartShortCompat
    total = 0
    v, p = _smart_s(b, p)
    while v == 32767:
        total += 32767
        v, p = _smart_s(b, p)
    return total + v, p

def decode_locs(b):
    """-> list of (id, level, x, z, shape, rot)"""
    p = 0; out = []; lid = -1
    while True:
        off, p = _int_smart_compat(b, p)
        if off == 0: break
        lid += off; pos = 0
        while True:
            po, p = _smart_s(b, p)
            if po == 0: break
            pos += po - 1
            attr = b[p]; p += 1
            out.append((lid, (pos >> 12) & 3, (pos >> 6) & 63, pos & 63, attr >> 2, attr & 3))
    if p != len(b): raise ValueError(f'loc walk {p} != {len(b)}')
    return out

def xtea_decrypt(data, key, rounds=32):
    """OSRS XTEA over whole 8-byte blocks; trailing bytes are left as they are."""
    out = bytearray(data)
    delta = 0x9E3779B9; mask = 0xFFFFFFFF
    for i in range(0, len(out) - len(out) % 8, 8):
        v0, v1 = struct.unpack('>II', out[i:i+8])
        s = (delta * rounds) & mask
        for _ in range(rounds):
            v1 = (v1 - ((((v0 << 4) ^ (v0 >> 5)) + v0) ^ (s + key[(s >> 11) & 3]))) & mask
            s = (s - delta) & mask
            v0 = (v0 - ((((v1 << 4) ^ (v1 >> 5)) + v1) ^ (s + key[s & 3]))) & mask
        out[i:i+8] = struct.pack('>II', v0, v1)
    return bytes(out)
