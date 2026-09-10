#!/usr/bin/env python3
"""Fill in the parts of an imported .obj that no cache carries: category, and the
combat-bonus block. Category is derived from wearpos, which OSRS does supply.

Skilling outfits have no combat bonuses and no level requirement in OSRS - they are
earned, not gated - so this deliberately writes zeroes rather than inventing numbers.
The per-piece experience bonuses ARE a real effect and are NOT implemented; each block
says so, the same way the Lumberjack and Void set effects do.
"""
import sys, re

CATEGORY = {
    'hat': 'armour_helmet', 'torso': 'armour_body', 'legs': 'armour_legs',
    'feet': 'armour_feet', 'hands': 'armour_hands', 'back': 'armour_cape',
    'lefthand': 'armour_shield',
}
TODO = '// TODO by hand: category, param= combat bonuses, equip requirement'


def main():
    path = sys.argv[1]
    text = open(path, newline='').read()
    crlf = '\r\n' in text
    lines = text.replace('\r\n', '\n').split('\n')

    out = []
    block = []
    def flush():
        if not block: return
        wearpos = None
        for l in block:
            if l.startswith('wearpos='): wearpos = l.split('=', 1)[1]
        cat = CATEGORY.get(wearpos)
        for l in block:
            if l == TODO:
                if cat: out.append(f'category={cat}')
                out.append('// Skilling outfits carry no combat bonuses and no equip')
                out.append('// requirement in OSRS - they are earned, not gated.')
                out.append('// NOT IMPLEMENTED: the per-piece experience bonus.')
            else:
                out.append(l)
        block.clear()

    for l in lines:
        if l.startswith('['):
            flush(); block.append(l)
        elif block or l == TODO:
            block.append(l)
        else:
            out.append(l)
    flush()

    res = '\n'.join(out)
    open(path, 'w', newline='').write(res.replace('\n', '\r\n') if crlf else res)
    n = sum(1 for l in out if l.startswith('category='))
    print(f'{path}: {n} blocks given a category')


if __name__ == '__main__':
    main()
