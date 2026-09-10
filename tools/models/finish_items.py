#!/usr/bin/env python3
"""Fill in category, combat bonuses and equip requirements for the OSRS wishlist items.

Numbers are the OSRS figures. Nothing here comes from the cache - the cache carries
no combat bonuses, no category and no equip requirement at all.
"""
import sys

TODO = '// TODO by hand: category, param= combat bonuses, equip requirement'

EXTRA = {
'slayer_helm': """category=armour_helmet
param=stabdefence,30
param=slashdefence,32
param=crushdefence,27
param=magicdefence,10
param=rangedefence,30
// Equip gate: 10 Defence, added in skill_slayer/scripts/slayer_helm.rs2.
// NOT IMPLEMENTED: the on-task damage/accuracy bonus. The black mask boost already
// exists in skill_combat (player_npc_hit_roll_boosted); wiring this helm into it is
// combat-script work, not config.""",
'dragon_pickaxe': """category=weapon_blunt
param=stabattack,33
param=slashattack,26
param=crushattack,-2
param=strengthbonus,45
// Equip gate: 60 Attack, added in tier60.rs2.
// NOT IMPLEMENTED: the special attack.""",
'magic_secateurs': """category=weapon_slash
param=slashattack,10
param=strengthbonus,10
// No equip requirement in OSRS.
// NOT IMPLEMENTED: the +10% herb yield when wielded - that is Farming-script work.""",
'imbued_heart': """// No wearpos in practice - it is an inventory item with an Invigorate option.
// NOT IMPLEMENTED: the magic level boost and its cooldown.""",
'herb_sack': """// NOT IMPLEMENTED: storage. The Fill/Open/Check/Empty options need a container
// varp and interface, the same shape the looting bag and seed box need.""",
'seed_box': """// NOT IMPLEMENTED: storage - see the note on the herb sack.""",
'looting_bag': """// NOT IMPLEMENTED: storage - see the note on the herb sack.""",
}


def main():
    path = sys.argv[1]
    text = open(path, newline='').read()
    crlf = '\r\n' in text
    lines = text.replace('\r\n', '\n').split('\n')
    out, current, done = [], None, set()
    for l in lines:
        if l.startswith('[') and l.endswith(']'):
            current = l[1:-1]
        if l == TODO:
            extra = EXTRA.get(current)
            if extra:
                out.extend(extra.split('\n')); done.add(current)
            else:
                out.append(l)
        else:
            out.append(l)
    res = '\n'.join(out)
    open(path, 'w', newline='').write(res.replace('\n', '\r\n') if crlf else res)
    missing = set(EXTRA) - done
    print(f'{path}: filled {len(done)} blocks' + (f'; NOT FOUND: {missing}' if missing else ''))


if __name__ == '__main__':
    main()
