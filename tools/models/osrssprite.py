#!/usr/bin/env python3
"""Decode an OSRS sprite group (cache index 8) into RGB images.

Format is read from the END of the buffer:
    last 2 bytes          sprite count
    len - 7 - count*8     width, height (g2 each), palette size - 1 (g1), then the four
                          arrays offsetX[], offsetY[], subWidth[], subHeight[] (g2 each),
                          which run exactly up to the count
    just before that      palette entries 1..n (g3 each); entry 0 is transparent
    from the start        per sprite: flags g1, then one palette index per pixel

Reconcile-or-reject: decode() returns None unless the pixel data consumes exactly the
region between offset 0 and the start of the trailer.
"""
import struct


def decode(b):
    if not b or len(b) < 10:
        return None
    n = int.from_bytes(b[-2:], 'big')
    if n <= 0 or n > 4096:
        return None
    head = len(b) - 7 - n * 8
    if head < 0:
        return None
    p = head
    def g2():
        nonlocal p
        v = int.from_bytes(b[p:p + 2], 'big'); p += 2; return v
    def g1():
        nonlocal p
        v = b[p]; p += 1; return v
    width, height = g2(), g2()
    pal_n = g1() + 1
    ox = [g2() for _ in range(n)]
    oy = [g2() for _ in range(n)]
    sw = [g2() for _ in range(n)]
    sh = [g2() for _ in range(n)]
    if p != len(b) - 2:                     # the four arrays must run exactly to the count
        return None
    # The palette sits immediately BEFORE the metadata block, not after it. Getting this
    # backwards is what made every texture sprite fail to decode on the first attempt: the
    # sizes still looked plausible, which is exactly why the exact-consumption check below
    # is the thing that decides, not whether the numbers seem reasonable.
    pal_end = head
    pp = pal_end - (pal_n - 1) * 3
    if pp < 0:
        return None
    data_end = pp                           # pixel data occupies [0, data_end)
    palette = [0] * pal_n
    for i in range(1, pal_n):
        palette[i] = int.from_bytes(b[pp:pp + 3], 'big'); pp += 3
        if palette[i] == 0:
            palette[i] = 1
    if pp != pal_end:
        return None

    q = 0
    sprites = []
    for i in range(n):
        w, h = sw[i], sh[i]
        if q >= data_end:
            return None
        flags = b[q]; q += 1
        px = [0] * (w * h)
        if w * h < 0 or q + w * h > data_end:
            return None
        if flags & 1:                       # column-major
            for x in range(w):
                for y in range(h):
                    px[y * w + x] = b[q]; q += 1
        else:                               # row-major
            for k in range(w * h):
                px[k] = b[q]; q += 1
        if flags & 2:                       # alpha channel follows, same order
            if q + w * h > data_end:
                return None
            q += w * h
        sprites.append(dict(w=w, h=h, ox=ox[i], oy=oy[i], px=px))
    if q != data_end:                       # must land exactly on the palette
        return None
    return dict(width=width, height=height, palette=palette, sprites=sprites)


def average_rgb(g, index=0):
    """Mean colour of a decoded sprite, ignoring fully transparent (palette 0) pixels."""
    s = g['sprites'][index]
    pal = g['palette']
    r = gsum = bsum = cnt = 0
    for v in s['px']:
        if v == 0:
            continue
        c = pal[v]
        r += c >> 16 & 0xFF; gsum += c >> 8 & 0xFF; bsum += c & 0xFF; cnt += 1
    if cnt == 0:
        return None
    return (r // cnt, gsum // cnt, bsum // cnt), cnt, len(s['px'])
