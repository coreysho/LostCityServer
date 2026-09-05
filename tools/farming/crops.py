# -*- coding: utf-8 -*-
"""Canonical 2006 farming crop table.

Every state number here was read out of the 377 cache (content/scripts/skill_farming/configs/farming.loc,
the multivar/multiloc blocks) rather than invented, so the client renders exactly what Jagex drew.
Universal rule established from that data:  visible_state = base + stage,  stage in [0..stages],
stage == stages is fully grown.  Diseased/dead/watered blocks are separate bases indexed by stage-1
(diseased/dead) or stage (watered).
Stats (levels, xp, protection payments, CTS) are the published 2006 values.
"""

# families
ALLOT, HOPS, FLOWER, HERB, BUSH, TREE, FRUIT, CACTUS, CALQUAT, MUSH, BELLA, SPIRIT = range(1, 13)

FAMILY_NAME = {ALLOT:'allotment', HOPS:'hops', FLOWER:'flower', HERB:'herb', BUSH:'bush', TREE:'tree',
               FRUIT:'fruit_tree', CACTUS:'cactus', CALQUAT:'calquat', MUSH:'mushroom',
               BELLA:'belladonna', SPIRIT:'spirit_tree'}

# cycle minutes per family
CYCLE = {ALLOT:10, HOPS:10, FLOWER:5, HERB:20, BUSH:20, TREE:40, FRUIT:160,
         CACTUS:80, CALQUAT:160, MUSH:40, BELLA:80, SPIRIT:320}

# fields: seed, fam, level, plant_xp*10, harvest_xp*10, check_xp*10, stages, base,
#         diseased, dead, watered, produce_base, produce_max, produce_obj,
#         cts_low, cts_high, disease/128, protect_obj, protect_qty, seeds_needed
C = []
def c(**k): C.append(k)

# ---------------------------------------------------------------- allotments (10 min/stage)
_al = dict(fam=ALLOT, cts_high=1800, disease=15, seeds=3)
c(seed='potato_seed',     level=1,  plant=80,   harvest=90,   stages=4, base=6,  dis=135, dead=199, wat=70,  produce='potato',     cts_low=1010, prot='bucket_compost', pq=2,  **_al)
c(seed='onion_seed',      level=5,  plant=95,   harvest=105,  stages=4, base=13, dis=142, dead=206, wat=77,  produce='onion',      cts_low=1050, prot='potato',         pq=10, **_al)
c(seed='cabbage_seed',    level=7,  plant=100,  harvest=115,  stages=4, base=20, dis=149, dead=213, wat=84,  produce='cabbage',    cts_low=1070, prot='onion',          pq=10, **_al)
c(seed='tomato_seed',     level=12, plant=125,  harvest=140,  stages=4, base=27, dis=156, dead=220, wat=91,  produce='tomato',     cts_low=1120, prot='cabbage',        pq=20, **_al)
c(seed='sweetcorn_seed',  level=20, plant=170,  harvest=190,  stages=6, base=34, dis=163, dead=227, wat=98,  produce='sweetcorn',  cts_low=880,  prot='jute_fibre',     pq=10, **_al)
c(seed='strawberry_seed', level=31, plant=260,  harvest=290,  stages=6, base=43, dis=172, dead=236, wat=107, produce='strawberry', cts_low=1030, prot='cooking_apple',  pq=5,  **_al)
c(seed='watermelon_seed', level=47, plant=485,  harvest=545,  stages=8, base=52, dis=181, dead=245, wat=116, produce='watermelon', cts_low=1260, prot='curry_leaf',     pq=10, **_al)

# ---------------------------------------------------------------- hops (10 min/stage)
_hp = dict(fam=HOPS, cts_high=1800, disease=15, seeds=4)
c(seed='barley_seed',          level=3,  plant=85,  harvest=95,  stages=4, base=49, dis=178, dead=242, wat=113, produce='barley',           cts_low=1030, prot='bucket_compost', pq=3,  **_hp)
c(seed='hammerstone_hop_seed', level=4,  plant=90,  harvest=100, stages=4, base=4,  dis=133, dead=197, wat=68,  produce='hammerstone_hops', cts_low=1040, prot='marigold',       pq=1,  **_hp)
c(seed='asgarnian_hop_seed',   level=8,  plant=109, harvest=120, stages=5, base=11, dis=140, dead=204, wat=75,  produce='asgarnian_hops',   cts_low=1080, prot='onion',          pq=10, **_hp)
c(seed='jute_seed',            level=13, plant=130, harvest=145, stages=5, base=56, dis=185, dead=249, wat=120, produce='jute_fibre',       cts_low=1130, prot='barley_malt',    pq=6,  fam=HOPS, cts_high=1800, disease=15, seeds=3)
c(seed='yanillian_hop_seed',   level=16, plant=145, harvest=160, stages=6, base=19, dis=148, dead=212, wat=83,  produce='yanillian_hops',   cts_low=1160, prot='tomato',         pq=5,  **_hp)
c(seed='krandorian_hop_seed',  level=21, plant=175, harvest=195, stages=7, base=28, dis=157, dead=221, wat=92,  produce='krandorian_hops',  cts_low=1210, prot='cabbage',        pq=30, **_hp)
c(seed='wildblood_hop_seed',   level=28, plant=230, harvest=260, stages=8, base=38, dis=167, dead=231, wat=102, produce='wildblood_hops',   cts_low=1280, prot='nasturtium',     pq=1,  **_hp)

# ---------------------------------------------------------------- flowers (5 min/stage, single yield)
_fl = dict(fam=FLOWER, stages=4, cts_low=0, cts_high=0, disease=13, seeds=1, prot=None, pq=0)
c(seed='marigold_seed',   level=2,  plant=85,  harvest=470,  base=8,  dis=137, dead=201, wat=72, produce='marigold',      **_fl)
c(seed='rosemary_seed',   level=11, plant=120, harvest=665,  base=13, dis=142, dead=206, wat=77, produce='rosemary',      **_fl)
c(seed='nasturtium_seed', level=24, plant=195, harvest=1110, base=18, dis=147, dead=211, wat=82, produce='nasturtium',    **_fl)
c(seed='woad_seed',       level=25, plant=205, harvest=1155, base=23, dis=152, dead=216, wat=87, produce='woadleaf',      **_fl)
c(seed='limpwurt_seed',   level=26, plant=215, harvest=1200, base=28, dis=157, dead=221, wat=92, produce='limpwurt_root', **_fl)

# ---------------------------------------------------------------- herbs (20 min/stage)
# All 14 herb blocks share the same generic models, so which block is which herb is a free choice;
# level order is used. Healthy bases come straight out of the cache; there is an 8-value hole at 60-67
# (the cache splits the 14 blocks 8 + 6 across the 64-value boundary), which is why this is a list and
# not base = 4 + 7*i.  Diseased is a tight 3-wide stride from 128; dead (170) is shared by every herb.
HERB_BASE = [4, 11, 18, 25, 32, 39, 46, 53, 68, 75, 82, 89, 96, 103]
HERBS = [
    ('guam_seed',       9,  110,  125,  'unidentified_guam',       250),
    ('marrentill_seed', 14, 135,  150,  'unidentified_marentill',  280),
    ('tarromin_seed',   19, 160,  180,  'unidentified_tarromin',   310),
    ('harralander_seed',26, 215,  240,  'unidentified_harralander',360),
    ('ranarr_seed',     32, 270,  305,  'unidentified_ranarr',     390),
    ('toadflax_seed',   38, 340,  385,  'unidentified_toadflax',   430),
    ('irit_seed',       44, 430,  485,  'unidentified_irit',       460),
    ('avantoe_seed',    50, 545,  615,  'unidentified_avantoe',    500),
    ('kwuarm_seed',     56, 690,  780,  'unidentified_kwuarm',     540),
    ('snapdragon_seed', 62, 875,  985,  'unidentified_snapdragon', 570),
    ('cadantine_seed',  67, 1065, 1200, 'unidentified_cadantine',  600),
    ('lantadyme_seed',  73, 1345, 1515, 'unidentified_lantadyme',  640),
    ('dwarf_weed_seed', 79, 1705, 1920, 'unidentified_dwarf_weed', 670),
    ('torstol_seed',    85, 1995, 2245, 'unidentified_torstol',    710),
]
for i, (sd, lv, px, hx, pr, ctsl) in enumerate(HERBS):
    c(seed=sd, fam=HERB, level=lv, plant=px, harvest=hx, stages=4, base=HERB_BASE[i],
      dis=128 + 3 * i, dead=170, wat=0, produce=pr, cts_low=ctsl, cts_high=800,
      disease=27, prot=None, pq=0, seeds=1)

# ---------------------------------------------------------------- bushes (20 min/stage, berries regrow)
_bs = dict(fam=BUSH, cts_low=0, cts_high=0, disease=18, seeds=1, wat=0)
c(seed='redberry_bush_seed',   level=10, plant=115,  harvest=45,  check=640,   stages=5, base=5,   dis=70,  dead=134, produce='redberries',       prot='cabbage',           pq=40, **_bs)
c(seed='cadavaberry_bush_seed',level=22, plant=180,  harvest=70,  check=1025,  stages=6, base=15,  dis=80,  dead=144, produce='cadavaberries',    prot='tomato',            pq=15, **_bs)
c(seed='dwellberry_bush_seed', level=36, plant=315,  harvest=120, check=1775,  stages=7, base=26,  dis=91,  dead=155, produce='dwellberries',     prot='strawberry',        pq=15, **_bs)
c(seed='jangerberry_bush_seed',level=48, plant=505,  harvest=190, check=2845,  stages=8, base=38,  dis=103, dead=167, produce='jangerberries',    prot='watermelon',        pq=6,  **_bs)
c(seed='whiteberry_bush_seed', level=59, plant=780,  harvest=290, check=4375,  stages=8, base=51,  dis=116, dead=180, produce='white_berries',    prot='bittercap_mushroom',pq=8,  **_bs)
c(seed='poisonivy_bush_seed',  level=70, plant=1200, harvest=450, check=6750,  stages=8, base=197, dis=210, dead=217, produce='poisonivy_berries',prot=None, pq=0, immune=1, **_bs)

# ---------------------------------------------------------------- trees (40 min/stage) - plant the sapling
_tr = dict(fam=TREE, harvest=0, cts_low=0, cts_high=0, seeds=1, wat=0)
c(seed='plantpot_oak_sapling',      level=15, plant=140,  check=46730,   stages=4,  base=8,  dis=73,  dead=137, produce=None,   disease=15, prot='tomato',       pq=5,  **_tr)
c(seed='plantpot_willow_sapling',   level=30, plant=250,  check=145650,  stages=6,  base=15, dis=80,  dead=144, produce=None,disease=13, prot='cooking_apple',pq=5,  **_tr)
c(seed='plantpot_maple_sapling',    level=45, plant=450,  check=340340,  stages=8,  base=24, dis=89,  dead=153, produce=None, disease=13, prot='orange',       pq=5,  **_tr)
c(seed='plantpot_yew_sapling',      level=60, plant=810,  check=706990,  stages=10, base=35, dis=100, dead=164, produce=None,   disease=11, prot='cactus_spine', pq=10, **_tr)
c(seed='plantpot_magic_tree_sapling',level=75,plant=1455, check=1376830, stages=12, base=48, dis=113, dead=177, produce=None, disease=9,  prot='coconut',      pq=25, **_tr)

# ---------------------------------------------------------------- fruit trees (160 min/stage)
_ft = dict(fam=FRUIT, cts_low=0, cts_high=0, stages=6, disease=18, seeds=1, wat=0)
c(seed='plantpot_apple_sapling',    level=27, plant=220,  harvest=85,  check=11995,  base=8,   dis=21,  dead=27,  produce='cooking_apple',prot='sweetcorn',     pq=9,  **_ft)
c(seed='plantpot_banana_sapling',   level=33, plant=280,  harvest=105, check=17505,  base=35,  dis=48,  dead=54,  produce='banana',       prot='cooking_apple', pq=20, **_ft)
c(seed='plantpot_orange_sapling',   level=39, plant=355,  harvest=135, check=24702,  base=72,  dis=85,  dead=91,  produce='orange',       prot='strawberry',    pq=15, **_ft)
c(seed='plantpot_curry_sapling',    level=42, plant=400,  harvest=150, check=29069,  base=99,  dis=112, dead=118, produce='curry_leaf',   prot='banana',        pq=25, **_ft)
c(seed='plantpot_pineapple_sapling',level=51, plant=570,  harvest=215, check=46627,  base=136, dis=149, dead=155, produce='pineapple',    prot='watermelon',    pq=10, **_ft)
c(seed='plantpot_papaya_sapling',   level=57, plant=720,  harvest=270, check=62184,  base=163, dis=176, dead=182, produce='papaya',       prot='pineapple',     pq=10, **_ft)
c(seed='plantpot_palm_sapling',     level=68, plant=1105, harvest=415, check=101501, base=200, dis=213, dead=219, produce='coconut',      prot='papaya',        pq=15, **_ft)

# ---------------------------------------------------------------- specials
c(seed='cactus_seed',   fam=CACTUS, level=55, plant=665,  harvest=250,  check=3740,  stages=7,  base=8, dis=19, dead=25, wat=0,
  produce='cactus_spine', cts_low=0, cts_high=0, disease=13, prot='cadavaberries', pq=6, seeds=1)
c(seed='plantpot_calquat_sapling', fam=CALQUAT, level=72, plant=1295, harvest=485, check=120960, stages=8, base=4, dis=19, dead=26, wat=0,
  produce='calquat_fruit', cts_low=0, cts_high=0, disease=13, prot='poisonivy_berries', pq=8, seeds=1)
c(seed='mushroom_seed', fam=MUSH, level=53, plant=615, harvest=577, stages=6, base=4, dis=16, dead=21, wat=0,
  produce='bittercap_mushroom', cts_low=0, cts_high=0, disease=13, prot=None, pq=0, seeds=1)
c(seed='belladonna_seed', fam=BELLA, level=63, plant=910, harvest=5120, stages=4, base=4, dis=9, dead=12, wat=0,
  produce='nightshade', cts_low=0, cts_high=0, disease=13, prot=None, pq=0, seeds=1)
c(seed='plantpot_spirit_tree_sapling', fam=SPIRIT, level=83, plant=1995, harvest=0, check=193010, stages=12, base=8, dis=21, dead=32, wat=0,
  produce=None, cts_low=0, cts_high=0, disease=9, prot=None, pq=0, seeds=1)

# The scarecrow is not grown - it is built from a hay sack, a bronze spear and a watermelon and then
# stood in a flower patch, where it protects the adjacent sweetcorn. Giving it a crop id lets it use
# exactly the same occupancy, clearing and protection code as a real flower.
c(seed='scarecrow_complete', fam=FLOWER, level=23, plant=0, harvest=0, stages=0, base=36,
  dis=0, dead=0, wat=0, produce=None, cts_low=0, cts_high=0, disease=0, prot=None, pq=0, seeds=1)

# Check-health / stump states, read out of the same cache tables.
#   chk  - what the patch shows while fully grown but not yet checked (the "Check-health" appearance)
#   chkd - what it shows after checking; for ordinary trees that is a second fully-grown model with
#          "Chop down" on it, for everything else it is the plain fully-grown state
#   stump- what is left after chopping a tree down, cleared with a spade
for x in C:
    f, b, s = x['fam'], x['base'], x['stages']
    g = b + s
    if f == TREE:
        x['chk'], x['chkd'], x['stump'] = g, g + 1, g + 2
    elif f == FRUIT:
        x['chk'], x['chkd'], x['stump'] = g + 20, g, g + 19
    elif f == CALQUAT:
        x['chk'], x['chkd'], x['stump'] = 34, g, 33
    elif f == CACTUS:
        x['chk'], x['chkd'], x['stump'] = 31, g, 0
    elif f == SPIRIT:
        x['chk'], x['chkd'], x['stump'] = 44, g, 0
    elif f == BUSH:
        x['chk'], x['chkd'], x['stump'] = 250 + C.index(x) - next(i for i, y in enumerate(C) if y['fam'] == BUSH), g, 0
    else:
        x['chk'], x['chkd'], x['stump'] = 0, g, 0

for i, x in enumerate(C):
    x['id'] = i + 1
    x.setdefault('check', 0)
    x.setdefault('immune', 0)
    x['cycle'] = CYCLE[x['fam']]
    # produce (harvest-count) display states, where the family has them
    f, b, s = x['fam'], x['base'], x['stages']
    if f in (BUSH, FRUIT, CALQUAT):
        x['pbase'], x['pmax'] = b + s + 1, (4 if f == BUSH else 6)
    elif f == CACTUS:
        x['pbase'], x['pmax'] = b + s + 1, 3
    elif f == MUSH:
        x['pbase'], x['pmax'] = b + s + 1, 6   # cache draws these in reverse; handled in rs2
    else:
        x['pbase'], x['pmax'] = 0, 0

CROPS = C
if __name__ == '__main__':
    for x in CROPS:
        print(x['id'], x['seed'], FAMILY_NAME[x['fam']], 'base', x['base'], 'stages', x['stages'],
              'grown', x['base'] + x['stages'], 'dis', x['dis'], 'dead', x['dead'], 'prod', x['pbase'], x['pmax'])
