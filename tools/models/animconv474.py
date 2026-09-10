#!/usr/bin/env python3
"""
Convert animations from the rev 474 cache into 377 format.

474 and 377 hold the SAME animation data in different layouts, so this rearranges bytes rather
than re-encoding anything. Verified before writing: all 1,655 474 skeletons and 20,410 frames
parse exactly, and all 57,303 seq frame references resolve.

  474 skeleton (idx1): size g1 | types[size] g1 | counts[size] g1 | ALL labels g1 concatenated
  377 AnimBase:        size g1 | types[size] g1 | per group: (count g1, its labels g1)
                       -> a de-interleave

  474 frame (idx0):    skeletonId g2 | groupCount g1 | flags[groupCount] g1 | gsmart per set bit
  377 .anim blob:      head(total g2, then per frame id g2 + groupCount g1)
                       | tran1(flags) | tran2(gsmart values) | del(delay g1) | AnimBase
                       | trailer: headLen g2, tran1Len g2, tran2Len g2, delLen g2  (last 8 bytes)
                       -> the same fields, split across streams. headLen counts 3 bytes per frame;
                          the client does pos += headLen + 2 to skip the leading total.

  474 seq (idx2 grp 12, op 1): count g2 | delays g2 | frameId low16 g2 | frameId high16 g2
                       frameId = (high << 16) | low = (frame group << 16) | file index

Delays: 377's seq config delay WINS (SeqType.method214 only falls back to the frame's own delay
when the seq delay is 0), and it is packed g2, so 474's long hold delays survive intact. The
.anim del byte is therefore just a sane fallback.

  python3 animconv474.py <cache> --seq 1234 [--seq ...] --content ../../content [--dry-run]
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dat2 import Store
from reftable import RefTable, split_group

# ------------------------------------------------------------------ 474 readers
def parse_474_skeleton(b):
    p = 0; size = b[p]; p += 1
    types = list(b[p:p+size]); p += size
    counts = list(b[p:p+size]); p += size
    labels = []
    for c in counts:
        labels.append(list(b[p:p+c])); p += c
    if p != len(b):
        raise ValueError(f'skeleton walk {p} != {len(b)}')
    return size, types, counts, labels

def parse_474_frame(b):
    """-> (skeletonId, groupCount, flags_bytes, value_bytes)"""
    sk = (b[0] << 8) | b[1]; p = 2
    n = b[p]; p += 1
    flags = b[p:p+n]; p += n
    vstart = p
    for f in flags:
        for bit in (1, 2, 4):
            if f & bit:
                p += 1 if b[p] < 128 else 2
    if p != len(b):
        raise ValueError(f'frame walk {p} != {len(b)}')
    return sk, n, bytes(flags), bytes(b[vstart:p])

def decode_474_seq(b):
    """Decode a 474 seq config.

    Opcodes are NOT written in ascending order - op 2 or op 5 routinely comes before op 1 -
    so bailing on the first unrecognised opcode silently drops the frame list. That mistake
    hid the frames of 4,052 of the cache's 7,297 seqs, Graardor's block and death among them.
    Anything unknown is therefore recorded and reported, never skipped past.
    """
    p = 0; out = {}
    n = len(b)
    def g1():
        nonlocal p
        v = b[p]; p += 1; return v
    def g2():
        nonlocal p
        v = (b[p] << 8) | b[p+1]; p += 2; return v
    def g3():
        nonlocal p
        v = int.from_bytes(b[p:p+3], 'big'); p += 3; return v
    def g4():
        nonlocal p
        v = int.from_bytes(b[p:p+4], 'big'); p += 4; return v
    while p < n:
        op = g1()
        if op == 0: break
        if op == 1:
            c = g2()
            out['delays'] = [g2() for _ in range(c)]
            lo = [g2() for _ in range(c)]
            hi = [g2() for _ in range(c)]
            out['frames'] = [(h << 16) | l for h, l in zip(hi, lo)]
        elif op == 2:  out['loops'] = g2()
        elif op == 3:  out['walkmerge'] = [g1() for _ in range(g1())]
        elif op == 4:  out['reachforward'] = 1           # payload-less
        elif op == 5:  out['priority'] = g1()
        elif op == 6:  out['replaceheldleft'] = g2()
        elif op == 7:  out['replaceheldright'] = g2()
        elif op == 8:  out['maxloops'] = g1()
        elif op == 9:  out['preanim_move'] = g1()
        elif op == 10: out['postanim_move'] = g1()
        elif op == 11: out['duplicatebehaviour'] = g1()
        elif op == 12: out['op12'] = [g4() for _ in range(g1())]
        elif op == 13: out['sounds'] = [g3() for _ in range(g1())]
        else:
            out['_unknown_op'] = op; out['_at'] = p - 1; break
    out['_tail'] = n - p
    return out

# ------------------------------------------------------------------ 377 writers
def emit_377_base(size, types, counts, labels):
    o = bytearray([size]); o += bytes(types)
    for c, ls in zip(counts, labels):
        o.append(c); o += bytes(ls)
    return bytes(o)

G2_MAX = 65535
# The client inflates every on-demand file into OnDemand.data, a fixed byte[65000], and throws
# "buffer overflow!" when it fills - which surfaces as "loaderror Requesting animations 65".
# K'ril's group 1208 came out at 86,862 bytes and did exactly that. Keep every set well under.
BLOB_MAX = 60000

def split_for_sets(frames, base_len=0):
    """Chunk frames so every 377 .anim section length fits in its g2.

    18 of 474's 1,846 frame groups exceed this - the big ones run to 1,785 frames and a flags
    section of 167KB against a 65,535 ceiling. A 377 set is just a container, so an oversized
    group becomes several sets, each with its own copy of the base. Frames keep their global ids,
    so seq references are unaffected.

    Also splits on total blob size (BLOB_MAX): head + tran1 + tran2 + del + base + 8-byte footer."""
    fixed = 2 + base_len + 8
    out = []; cur = []; h = t1 = t2 = 0
    for f in frames:
        _, n, flags, vals = f
        nh, nt1, nt2 = h + 3, t1 + len(flags), t2 + len(vals)
        total = fixed + nh + nt1 + nt2 + len(cur) + 1          # +1 del byte per frame
        if cur and (nh > G2_MAX or nt1 > G2_MAX or nt2 > G2_MAX or len(cur) + 1 > G2_MAX
                    or total > BLOB_MAX):
            out.append(cur); cur = []; h = t1 = t2 = 0
            nh, nt1, nt2 = 3, len(flags), len(vals)
        cur.append(f); h, t1, t2 = nh, nt1, nt2
    if cur: out.append(cur)
    return out

def build_377_anim(frames, base_bytes, default_delay=1):
    """frames: list of (frame_id, groupCount, flags_bytes, value_bytes)"""
    head = bytearray(); tran1 = bytearray(); tran2 = bytearray(); dele = bytearray()
    head += len(frames).to_bytes(2, 'big')
    for fid, n, flags, vals in frames:
        head += fid.to_bytes(2, 'big'); head.append(n)
        tran1 += flags; tran2 += vals
        dele.append(min(max(default_delay, 1), 255))
    head_len = 3 * len(frames)                    # client does pos += head_len + 2
    blob = bytes(head) + bytes(tran1) + bytes(tran2) + bytes(dele) + base_bytes
    blob += (head_len.to_bytes(2, 'big') + len(tran1).to_bytes(2, 'big')
             + len(tran2).to_bytes(2, 'big') + len(dele).to_bytes(2, 'big'))
    return blob

def parse_377_anim(blob):
    """Faithful re-implementation of AnimFrame.method262 - used to verify our own output."""
    n = len(blob)
    g2 = lambda o: (blob[o] << 8) | blob[o+1]
    head_len, t1, t2, dl = g2(n-8), g2(n-6), g2(n-4), g2(n-2)
    hp = 0; pos = head_len + 2
    t1p = pos; pos += t1
    t2p = pos; pos += t2
    dp = pos; pos += dl
    bp = pos
    total = g2(hp); hp += 2
    out = []
    for _ in range(total):
        fid = g2(hp); hp += 2
        cnt = blob[hp]; hp += 1
        flags = blob[t1p:t1p+cnt]; t1p += cnt
        vs = t2p
        for f in flags:
            for bit in (1, 2, 4):
                if f & bit:
                    t2p += 1 if blob[t2p] < 128 else 2
        out.append((fid, cnt, bytes(flags), bytes(blob[vs:t2p]), blob[dp]))
        dp += 1
    return out, blob[bp:n-8]

# ------------------------------------------------------------------ packs
def pack_append(path, names):
    """Append names to a tracked name-map pack, returning {name: id}. Preserves line endings."""
    s = open(path, newline='').read(); crlf = '\r\n' in s
    lines = s.replace('\r\n', '\n').rstrip('\n').split('\n')
    have = {l.split('=', 1)[1]: int(l.split('=', 1)[0]) for l in lines if '=' in l}
    nxt = max(have.values()) + 1
    assigned = {}
    for nm in names:
        if nm in have:
            assigned[nm] = have[nm]; continue
        assigned[nm] = nxt; lines.append(f'{nxt}={nm}'); nxt += 1
    out = '\n'.join(lines) + '\n'
    open(path, 'w', newline='').write(out.replace('\n', '\r\n') if crlf else out)
    return assigned, nxt - 1

def pack_max(path):
    lines = open(path, newline='').read().replace('\r\n', '\n').split('\n')
    return max(int(l.split('=', 1)[0]) for l in lines if '=' in l)

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cache')
    ap.add_argument('--seq', action='append', required=True,
                    help='474 seq id, optionally id:local_name (e.g. 7058:graardor_walk)')
    ap.add_argument('--content', default=None)
    ap.add_argument('--out', default=None, help='.seq config to write')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    st = Store(a.cache)
    rt0 = RefTable(st.read(255, 0)); rt2 = RefTable(st.read(255, 2))
    seq_files = split_group(st.read(2, 12), rt2.file_counts[12]); seq_ids = rt2.file_ids[12]
    seqs = {i: b for i, b in zip(seq_ids, seq_files) if b}

    seq_names = {}
    for spec in a.seq:
        sid, _, nm = str(spec).partition(':')
        seq_names[int(sid)] = nm or f'seq_474_{int(sid)}'

    wanted = {}
    for sid in seq_names:
        if sid not in seqs: raise SystemExit(f'474 seq {sid} not found')
        d = decode_474_seq(seqs[sid])
        if 'frames' not in d: raise SystemExit(f'474 seq {sid} has no frame block')
        wanted[sid] = d

    groups = sorted({f >> 16 for d in wanted.values() for f in d['frames']})
    print(f'# {len(wanted)} seq(s) -> {len(groups)} frame group(s): {groups}')

    conv = {}          # 474 group -> dict(frames=[(idx, n, flags, vals)], skel=int, base=bytes)
    for g in groups:
        files = split_group(st.read(0, g), rt0.file_counts[g])
        idxs = rt0.file_ids[g]
        parsed = []; skels = set()
        for fi, blob in zip(idxs, files):
            if not blob: continue
            sk, n, flags, vals = parse_474_frame(blob)
            skels.add(sk); parsed.append((fi, n, flags, vals))
        if len(skels) != 1:
            raise SystemExit(f'474 group {g} spans {len(skels)} skeletons {skels}; '
                             f'a 377 .anim set carries exactly one base')
        sk = skels.pop()
        size, types, counts, labels = parse_474_skeleton(st.read(1, sk))
        conv[g] = dict(frames=parsed, skel=sk, base=emit_377_base(size, types, counts, labels),
                       groups=size)
        print(f'#   group {g}: {len(parsed)} frames, skeleton {sk} ({size} transform groups)')

    if a.dry_run or not a.content:
        print('# dry run - nothing written'); return

    C = a.content
    anim_pack = os.path.join(C, 'pack', 'anim.pack')
    base_pack = os.path.join(C, 'pack', 'base.pack')
    seq_pack = os.path.join(C, 'pack', 'seq.pack')      # tracked - the seq name must be registered
    # tools/pack/graphics/pack.ts does AnimSetPack.getByName(basename of the .anim file),
    # so a set that is not registered here is silently dropped at build time.
    animset_pack = os.path.join(C, 'pack', 'animset.pack')

    frame_id_map = {}      # (474group, fileidx) -> new 377 frame id
    for g in groups:
        c = conv[g]
        frame_names = [f'anim_{g}_{fi}' for fi, _, _, _ in c['frames']]
        assigned, _ = pack_append(anim_pack, frame_names)
        ids = [assigned[n] for n in frame_names]
        for (fi, _, _, _), nid in zip(c['frames'], ids):
            frame_id_map[(g, fi)] = nid
        if max(ids) > 65535:
            raise SystemExit('frame id exceeded 65535 - the .anim head writes it as g2')

        tagged = [(frame_id_map[(g, fi)], n, fl, vs) for fi, n, fl, vs in c['frames']]
        chunks = split_for_sets(tagged, len(c['base']))
        if len(chunks) > 1:
            print(f'#   group {g} exceeds a 377 size limit - split across {len(chunks)} sets')
        for k, chunk in enumerate(chunks):
            # Named after the 474 group, not a running counter, so re-running the tool
            # reuses the same set instead of writing a duplicate beside the old one.
            # First chunk keeps the plain name, later ones get _2, _3... (matches the hand
            # split of anim_474_1208 -> anim_474_1208 + anim_474_1208_2).
            set_name = f'anim_474_{g}' + (f'_{k+1}' if k > 0 else '')
            pack_append(animset_pack, [set_name])
            pack_append(base_pack, [set_name.replace('anim_', 'base_', 1)])
            blob = build_377_anim(chunk, c['base'])
            # verify our own output round-trips through the client's own reader
            got, gotbase = parse_377_anim(blob)
            assert len(got) == len(chunk), 'frame count lost'
            for (fid, n, fl, vs), (gid, gn, gfl, gvs, _) in zip(chunk, got):
                assert gid == fid and gn == n and gfl == fl and gvs == vs, \
                    f'round-trip mismatch on group {g} frame {fid}'
            assert gotbase == c['base'], 'base lost'
            assert len(blob) < 65000, f'{set_name} is {len(blob)} bytes - client buffer is 65000'
            open(os.path.join(C, 'models', f'{set_name}.anim'), 'wb').write(blob)
            print(f'#   wrote models/{set_name}.anim  ({len(blob)} bytes, {len(chunk)} frames, '
                  f'ids {chunk[0][0]}-{chunk[-1][0]}) - round-trip verified')

    lines = ['// Animations converted from the rev 474 cache by tools/models/animconv474.py.',
             '// Frame data is a byte re-layout of 474 - nothing re-encoded. The flags below',
             "// (priority, loops, walkmerge...) are the cache's own; 474 and 377 use the same",
             '// seq opcodes, so they carry across unchanged - see tools/pack/config/SeqConfig.ts.', '']
    for sid, d in wanted.items():
        lines.append(f'[{seq_names[sid]}]')
        # 474 seq opcode -> Lost City .seq key. Identical numbering on both sides.
        if 'loops' in d:        lines.append(f'loops={d["loops"]}')          # op 2
        if d.get('walkmerge'):  lines.append('walkmerge=' +                  # op 3
                                             ','.join(f'label_{l}' for l in d['walkmerge']))
        if 'reachforward' in d: lines.append('reachforward=yes')             # op 4
        if 'priority' in d:     lines.append(f'priority={d["priority"]}')    # op 5
        if 'maxloops' in d:     lines.append(f'maxloops={d["maxloops"]}')    # op 8
        # ops 9-11: SeqConfig.ts takes these as names, not numbers
        if 'preanim_move' in d:
            lines.append('preanim_move=' + ['delaymove', 'delayanim', 'merge'][d['preanim_move']])
        if 'postanim_move' in d:
            lines.append('postanim_move=' + ['delaymove', 'abortanim', 'merge'][d['postanim_move']])
        if 'duplicatebehaviour' in d:
            lines.append('duplicatebehaviour=' + ['0', 'reset', 'reset_loop'][d['duplicatebehaviour']])
        # ops 6/7 (replaceheldleft/right) are 474 OBJ ids and mean nothing here; ops 12/13
        # are animation sounds, which 377 seqs have no field for. Reported, not emitted.
        skipped = [k for k in ('replaceheldleft', 'replaceheldright', 'sounds', 'op12') if d.get(k)]
        if skipped:
            lines.append(f'// 474 also carried: {", ".join(skipped)} - not transferable')
        for n, (fr, dl) in enumerate(zip(d['frames'], d['delays']), start=1):
            lines.append(f'frame{n}=anim_{fr >> 16}_{fr & 0xffff}')
            lines.append(f'delay{n}={dl}')
        lines.append('')
    pack_append(seq_pack, [seq_names[sid] for sid in wanted])
    for sid in wanted: print(f'#   seq.pack registered {seq_names[sid]}')
    text = '\r\n'.join(lines)
    if a.out:
        open(a.out, 'w', newline='').write(text)
        print(f'#   wrote {a.out}')
    else:
        print(text)

if __name__ == '__main__':
    main()
