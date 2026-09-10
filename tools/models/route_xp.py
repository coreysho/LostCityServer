#!/usr/bin/env python3
"""Route stat_advance calls for the outfit skills through the bonus procs.

Rewrites  stat_advance(mining, <expr>);  ->  ~mining_xp(<expr>);

The argument is matched by walking balanced parentheses, not by regex, because plenty
of these calls wrap calc(...) or nested proc calls and a lazy match would cut them in
half. Line endings are preserved, and the file this module itself lives in is skipped
so the procs do not rewrite their own stat_advance calls into infinite recursion.
"""
import os, sys

SKILLS = ['mining', 'fishing', 'woodcutting', 'firemaking', 'runecraft', 'smithing']
SKIP = {'outfit_xp.rs2'}

# Only the core skill paths are routed. In OSRS these outfits boost experience from the
# ACTIVITY, not lump-sum quest rewards or minigame payouts, so quests/, minigames/ and
# area scripts are deliberately left alone. Pass --all to route everything instead.
INCLUDE = ('/skill_',)


def rewrite(text, skill):
    needle = f'stat_advance({skill},'
    out, i, n = [], 0, 0
    while True:
        j = text.find(needle, i)
        if j < 0:
            out.append(text[i:]); break
        # walk to the matching close paren of stat_advance(
        k = j + len('stat_advance(')
        depth = 1
        while k < len(text) and depth:
            if text[k] == '(': depth += 1
            elif text[k] == ')': depth -= 1
            k += 1
        if depth:                       # unbalanced - leave it alone
            out.append(text[i:j + len(needle)]); i = j + len(needle); continue
        arg = text[j + len(needle):k - 1].strip()
        out.append(text[i:j])
        out.append(f'~{skill}_xp({arg})')
        i = k; n += 1
    return ''.join(out), n


def main():
    root = sys.argv[1]
    dry = '--dry-run' in sys.argv
    total, touched = 0, []
    for r, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith('.rs2') or f in SKIP: continue
            p = os.path.join(r, f)
            rel = p.replace(os.sep, '/')
            if '--all' not in sys.argv and not any(k in rel for k in INCLUDE):
                continue
            raw = open(p, newline='').read()
            crlf = '\r\n' in raw
            text = raw.replace('\r\n', '\n')
            before = text
            count = 0
            for s in SKILLS:
                text, c = rewrite(text, s); count += c
            if count:
                total += count; touched.append((p, count))
                if not dry:
                    open(p, 'w', newline='').write(text.replace('\n', '\r\n') if crlf else text)
    for p, c in sorted(touched):
        print(f'  {c:>3}  {p}')
    print(f'{total} call sites in {len(touched)} files' + ('  (dry run)' if dry else '  rewritten'))


if __name__ == '__main__':
    main()
