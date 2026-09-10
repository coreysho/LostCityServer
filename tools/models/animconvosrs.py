#!/usr/bin/env python3
"""
Convert animations from a modern OSRS cache (the .flatcache dump in caches/newest cache) into
377 .anim sets + a .seq config.

OSRS still stores classic frame animations exactly like 474 does - same framemap (skeleton)
layout, same frame layout, same seq opcode 1 - so this reuses animconv474's byte re-layout and
its round-trip check. What differs:

  * Seq configs use the rev 226+ opcodes (osrsseq.py). Seqs driven by the new skeletal system
    (op 13, "animmaya") have no classic frames and are refused.
  * OSRS framemaps may carry trailing bytes after the label lists (skeleton 0, the player
    skeleton, ends in two zero bytes). They are ignored; the 377 base is built from the groups.
  * Only frames the chosen seqs actually use are converted, not the whole frame group, so a
    group that holds hundreds of unrelated frames does not burn anim.pack ids.

OSRS re-rigged the player animations on its own skeleton 0 (245 transform groups; 377's player
base has 117), so these frames must play on their own base. A 377-skeleton animation and an
OSRS one must never be walk-merged together - the client patch in ClientPlayer/NpcType skips the
merge when the two frames use different bases.

Names: frames anim_osrs_<group>_<file>, sets anim_osrs_<group> (+ _2, _3 when split), bases
base_osrs_<group>. Seqs are named on the command line.

  python3 animconvosrs.py "<newest cache>" --seq 1658:osrs_whip_attack [--seq ...] \
      --content ../../content --out ../../content/scripts/<area>/configs/<file>.seq [--dry-run]
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatcache import Store
from reftable import split_group
from osrsseq import decode_osrs_seq
from animconv474 import (parse_474_frame, emit_377_base, split_for_sets, build_377_anim,
                         parse_377_anim, pack_append)

def parse_osrs_framemap(b):
    """Same as a 474 skeleton; trailing bytes (newer revisions) are allowed and ignored."""
    p = 0; size = b[p]; p += 1
    types = list(b[p:p+size]); p += size
    counts = list(b[p:p+size]); p += size
    labels = []
    for c in counts:
        labels.append(list(b[p:p+c])); p += c
    if p > len(b):
        raise ValueError('framemap truncated')
    extra = b[p:]
    return size, types, counts, labels, bytes(extra)

def load_osrs_seqs(st):
    rt = st.reftable(2)
    ids = rt.file_ids[12]
    files = split_group(st.read(2, 12), len(ids))
    return {i: f for i, f in zip(ids, files) if f}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache')
    ap.add_argument('--seq', action='append', required=True,
                    help='OSRS seq id:local_name, e.g. 1658:osrs_whip_attack')
    ap.add_argument('--content', default=None)
    ap.add_argument('--out', default=None, help='.seq config to write')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    st = Store(a.cache)
    seqs = load_osrs_seqs(st)
    names = {}
    for spec in a.seq:
        sid, _, nm = str(spec).partition(':')
        names[int(sid)] = nm or f'seq_osrs_{int(sid)}'

    wanted = {}
    for sid in names:
        if sid not in seqs: raise SystemExit(f'OSRS seq {sid} not found')
        d = decode_osrs_seq(seqs[sid])
        if 'animmaya' in d and not d.get('frames'):
            raise SystemExit(f'OSRS seq {sid} is a skeletal (animmaya) animation - no classic frames')
        if not d.get('frames'): raise SystemExit(f'OSRS seq {sid} has no frames')
        wanted[sid] = d

    used = {}                                   # group -> sorted file ids actually referenced
    for d in wanted.values():
        for f in d['frames']:
            used.setdefault(f >> 16, set()).add(f & 0xffff)
    groups = sorted(used)
    print(f'# {len(wanted)} seq(s) -> {len(groups)} frame group(s): {groups}')

    rt0 = st.reftable(0)
    conv = {}
    for g in groups:
        idxs = rt0.file_ids[g]
        files = split_group(st.read(0, g), len(idxs))
        parsed = []; skels = set()
        for fi, blob in zip(idxs, files):
            if fi not in used[g]: continue
            sk, n, flags, vals = parse_474_frame(blob)
            skels.add(sk); parsed.append((fi, n, flags, vals))
        missing = used[g] - {p[0] for p in parsed}
        if missing: raise SystemExit(f'group {g}: frames {sorted(missing)} not in cache')
        if len(skels) != 1:
            raise SystemExit(f'group {g} spans skeletons {skels}; a 377 set carries one base')
        sk = skels.pop()
        size, types, counts, labels, extra = parse_osrs_framemap(st.read(1, sk))
        for fi, n, fl, vs in parsed:
            if n > size: raise SystemExit(f'group {g} frame {fi}: {n} groups > skeleton {size}')
        conv[g] = dict(frames=parsed, skel=sk, base=emit_377_base(size, types, counts, labels))
        print(f'#   group {g}: {len(parsed)} frame(s) used, skeleton {sk} ({size} groups'
              + (f', {len(extra)} trailing byte(s) ignored' if extra else '') + ')')

    if a.dry_run or not a.content:
        for sid, d in wanted.items():
            print(f'#   seq {sid} {names[sid]}: {len(d["frames"])} frames, '
                  f'{ {k: v for k, v in d.items() if k not in ("frames", "delays")} }')
        print('# dry run - nothing written'); return

    C = a.content
    anim_pack = os.path.join(C, 'pack', 'anim.pack')
    base_pack = os.path.join(C, 'pack', 'base.pack')
    seq_pack = os.path.join(C, 'pack', 'seq.pack')
    animset_pack = os.path.join(C, 'pack', 'animset.pack')

    fid = {}
    for g in groups:
        c = conv[g]
        frame_names = [f'anim_osrs_{g}_{fi}' for fi, _, _, _ in c['frames']]
        assigned, _ = pack_append(anim_pack, frame_names)
        for (fi, _, _, _), nm in zip(c['frames'], frame_names):
            fid[(g, fi)] = assigned[nm]
        if max(assigned.values()) > 65535:
            raise SystemExit('frame id exceeded 65535 - the .anim head writes it as g2')
        tagged = [(fid[(g, fi)], n, fl, vs) for fi, n, fl, vs in c['frames']]
        chunks = split_for_sets(tagged, len(c['base']))
        for k, chunk in enumerate(chunks):
            set_name = f'anim_osrs_{g}' + (f'_{k+1}' if k > 0 else '')
            pack_append(animset_pack, [set_name])
            pack_append(base_pack, [set_name.replace('anim_', 'base_', 1)])
            blob = build_377_anim(chunk, c['base'])
            got, gotbase = parse_377_anim(blob)
            assert len(got) == len(chunk)
            for (i1, n, fl, vs), (i2, gn, gfl, gvs, _) in zip(chunk, got):
                assert i1 == i2 and n == gn and fl == gfl and vs == gvs, f'round-trip {g}/{i1}'
            assert gotbase == c['base']
            assert len(blob) < 65000, f'{set_name} is {len(blob)} bytes'
            open(os.path.join(C, 'models', f'{set_name}.anim'), 'wb').write(blob)
            print(f'#   wrote models/{set_name}.anim ({len(blob)} bytes, {len(chunk)} frames)')

    lines = ['// Animations converted from the OSRS cache by tools/models/animconvosrs.py.',
             '// They play on the OSRS player skeleton (base_osrs_*), not the 377 one: the client',
             '// only walk-merges two animations that share a base (ClientPlayer/NpcType patch).', '']
    for sid, d in wanted.items():
        lines.append(f'[{names[sid]}]')
        lines.append(f'// OSRS seq {sid}')
        if 'loops' in d:        lines.append(f'loops={d["loops"]}')
        if d.get('walkmerge'):  lines.append('walkmerge=' + ','.join(f'label_{l}' for l in d['walkmerge']))
        if d.get('reachforward'): lines.append('reachforward=yes')
        if 'priority' in d:     lines.append(f'priority={d["priority"]}')
        if 'maxloops' in d:     lines.append(f'maxloops={d["maxloops"]}')
        # SeqConfig.ts takes these as names, not numbers
        if 'preanim_move' in d:
            lines.append('preanim_move=' + ['delaymove', 'delayanim', 'merge'][d['preanim_move']])
        if 'postanim_move' in d:
            lines.append('postanim_move=' + ['delaymove', 'abortanim', 'merge'][d['postanim_move']])
        if 'duplicatebehaviour' in d:
            lines.append('duplicatebehaviour=' + ['0', 'reset', 'reset_loop'][d['duplicatebehaviour']])
        skipped = [k for k in ('replaceheldleft', 'replaceheldright', 'sounds') if d.get(k)]
        if skipped: lines.append(f'// OSRS also carried: {", ".join(skipped)} - not transferable')
        for n, (fr, dl) in enumerate(zip(d['frames'], d['delays']), start=1):
            lines.append(f'frame{n}=anim_osrs_{fr >> 16}_{fr & 0xffff}')
            lines.append(f'delay{n}={dl}')
        lines.append('')
    pack_append(seq_pack, [names[sid] for sid in wanted])
    text = '\r\n'.join(lines)
    if a.out:
        open(a.out, 'w', newline='').write(text); print(f'#   wrote {a.out}')
    else:
        print(text)

if __name__ == '__main__':
    main()
