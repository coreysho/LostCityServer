#!/usr/bin/env python3
"""Build content/sprites/bankbuttons.png out of the OSRS cache.

The bank's bottom button bar wants OSRS's own art. Every sprite here is lifted from the OSRS
sprite index (idx8) of `caches/newest cache` and pasted, centred, into a 36x36 tile - 36 being
both the size of OSRS's own button background (sprite 170) and the height of the row the buttons
sit on. The packer (tools/pack/sprite/media.ts, via content/sprites/meta/bankbuttons.opt) slices
the strip back into tiles on that 36x36 grid, so THE ORDER BELOW IS THE SPRITE INDEX and has to
match content/tools/genbankbar.py's BG_OFF / BG_ON / ICON_* constants.

Magenta (0xFF00FF) is the packer's transparent colour, so any source pixel that happens to be
exactly magenta is nudged to 0xFE00FE - invisible to the eye, and not a hole.

The sheet is committed, so a normal build never touches the OSRS cache. Run this only when the
sheet needs changing, from anywhere:  python tools/models/genbanksprites.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # the LostCityServer working copy
CACHE = os.path.join(ROOT, 'caches', 'newest cache')
OUT = os.path.join(ROOT, 'content', 'sprites', 'bankbuttons.png')
META = os.path.join(ROOT, 'content', 'sprites', 'meta', 'bankbuttons.opt')

TILE = 36

# index -> (osrs sprite group, what it is). The four toggle icons are the ones OSRS's own bank
# uses: interface 12 hangs sprite 2820 off its rearrange button and 2822 off its withdraw-as
# button, and swaps in 2821 / 2823 for the other state of each.
SHEET = [
    (170, 'button background, unlit'),
    (179, 'button background, lit'),
    (2820, 'rearrange: swap'),
    (2821, 'rearrange: insert'),
    (2823, 'withdraw as: item'),
    (2822, 'withdraw as: note'),
    (1043, 'search'),
    (1041, 'deposit inventory'),
    (1042, 'deposit worn items'),
    (1342, 'padlock - unused, kept for placeholders'),
]


def main():
    sys.path.insert(0, HERE)
    from flatcache import Store
    import osrssprite
    from PIL import Image

    st = Store(CACHE)
    sheet = Image.new('RGB', (TILE * len(SHEET), TILE), (255, 0, 255))
    for i, (gid, what) in enumerate(SHEET):
        g = osrssprite.decode(st.read(8, gid))
        s = g['sprites'][0]
        pal = g['palette']
        if s['w'] > TILE or s['h'] > TILE:
            sys.exit(f'sprite {gid} is {s["w"]}x{s["h"]}, too big for a {TILE}px tile')
        ox = i * TILE + (TILE - s['w']) // 2
        oy = (TILE - s['h']) // 2
        for y in range(s['h']):
            for x in range(s['w']):
                v = s['px'][y * s['w'] + x]
                if not v:
                    continue
                c = pal[v]
                rgb = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
                if rgb == (255, 0, 255):
                    rgb = (254, 0, 254)
                sheet.putpixel((ox + x, oy + y), rgb)
        print(f'{i:2}  gid {gid:5}  {s["w"]}x{s["h"]:<6} {what}')
    sheet.save(OUT)
    with open(META, 'w', newline='\n') as fh:
        fh.write(f'{TILE}x{TILE}\n')
    print(f'{OUT}  {sheet.width}x{sheet.height}, {len(SHEET)} tiles')


main()
