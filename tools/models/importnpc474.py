#!/usr/bin/env python3
"""Import a 474 npc's models and emit a Lost City .npc config skeleton.

Animations are NOT handled here - convert those first with animconv474.py and pass
the local seq names in. Models, model.pack and npc.pack are handled here.

  python3 tools/models/importnpc474.py <cache> --npc 6260 --name graardor \
      --dir content/scripts/bosses/godwars --ready graardor_ready --walk graardor_walk
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store
from npcconfig474 import load_all as load_npcs
from animconv474 import pack_append


def hsl16_to_rgb15_table():
    """Reverse of ColorConversion.rgb15toHsl16, built by forward-mapping every rgb15."""
    from ob2render import rgb15_to_hsl16          # cloud-only import; guarded by caller
    return {rgb15_to_hsl16(v): v for v in range(32768)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache'); ap.add_argument('--npc', type=int, required=True)
    ap.add_argument('--name', required=True, help='local name, e.g. graardor')
    ap.add_argument('--dir', required=True, help='content/scripts/<area> - configs/ is written under it')
    ap.add_argument('--content', default='content')
    ap.add_argument('--ready'); ap.add_argument('--walk')
    ap.add_argument('--attack'); ap.add_argument('--defend'); ap.add_argument('--death')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    st = Store(a.cache)
    n = load_npcs(a.cache)[a.npc]
    print(f'# 474 npc {a.npc}: {n.get("name")}  size={n.get("size")}  '
          f'models={n["models"]}  recols={len(n["recol"])}')
    if n['recol']:
        print('# NOTE: this npc has cache recolours; they are emitted raw as HSL16 and '
              'must be checked against the model before shipping')

    model_pack = os.path.join(a.content, 'pack', 'model.pack')
    npc_pack = os.path.join(a.content, 'pack', 'npc.pack')
    mdir = os.path.join(a.content, 'models', 'npc')

    mnames = [f'npc_{a.name}_{i+1}' for i in range(len(n['models']))]
    lines = [f'// {n.get("name")} - imported from the rev 474 cache '
             f'(npc {a.npc}) by tools/models/importnpc474.py.',
             '// Models copied byte-for-byte; the 474 cache carries no combat stats, so',
             '// TODO by hand: hitpoints, attack/strength/defence, param= bonuses, huntmode, drops.',
             '', f'[{a.name}]', f'name={n.get("name")}',
             f'desc={n.get("name")}.']
    for i, mn in enumerate(mnames, start=1):
        lines.append(f'model{i}={mn}')
    if n.get('size'):     lines.append(f'size={n["size"]}')
    if a.ready:           lines.append(f'readyanim={a.ready}')
    if a.walk:            lines.append(f'walkanim={a.walk}')
    if n.get('resizeh'):  lines.append(f'resizeh={n["resizeh"]}')
    if n.get('resizev'):  lines.append(f'resizev={n["resizev"]}')
    for k, v in sorted((n.get('ops') or {}).items()):
        lines.append(f'op{k+1}={v}')
    if n.get('vislevel'): lines.append(f'vislevel={n["vislevel"]}')
    for k, v in (('attack_anim', a.attack), ('defend_anim', a.defend), ('death_anim', a.death)):
        if v: lines.append(f'param={k},{v}')
    lines.append('')

    text = '\r\n'.join(lines)
    print('\n' + text)
    if a.dry_run:
        print('# dry run - nothing written'); return

    assigned, _ = pack_append(model_pack, mnames)
    os.makedirs(mdir, exist_ok=True)
    for src, mn in zip(n['models'], mnames):
        open(os.path.join(mdir, f'{mn}.ob2'), 'wb').write(st.read(7, src))
        print(f'#   models/npc/{mn}.ob2  <- 474 model {src}  (model.pack {assigned[mn]})')
    npc_assigned, _ = pack_append(npc_pack, [a.name])
    print(f'#   npc.pack {npc_assigned[a.name]}={a.name}')

    cdir = os.path.join(a.dir, 'configs')
    os.makedirs(cdir, exist_ok=True)
    out = os.path.join(cdir, f'{a.name}.npc')
    open(out, 'w', newline='').write(text)
    print(f'#   wrote {out}')


if __name__ == '__main__':
    main()
