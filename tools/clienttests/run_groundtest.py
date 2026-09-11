#!/usr/bin/env python3
"""
Runs the headless harness for Client.drawGroundItems().

The point of the extraction: the method body is pulled out of Client.java every run, so the test
exercises the source that actually ships. A harness with a hand-copied body proves only that the
copy works - which is exactly the trap that let a model converter round-trip cleanly against its
own reader while dropping face priorities on the floor.

    python3 run_groundtest.py [path\\to\\javaclient]

Needs javac/java on PATH. Writes its scratch to a temp dir; nothing is left behind.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLIENT_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'javaclient'))

METHOD_START = '\tprivate void updateAltState() {'
METHOD_END = '\n\tprivate void drawXpDrops()'
CONST_START = '\tprivate static final int GROUND_ITEM_ROW_H'
CONST_END = '\tprivate final int[] giZoneNameEndX = new int[GROUND_ITEM_MAX_LABELS];'
# Lives with the other panels' constants, not the ground item block, but handleGroundItemClick
# needs it. Extracted rather than retyped so a change to the viewport offset cannot pass a test.
CONSTANTS = ['\tprivate static final int QOL_PANEL_ORIGIN = 4;']


def extract(client_path):
    # newline='' so the file's CRLF endings survive the read; the repo's java sources are CRLF.
    with open(client_path, newline='') as f:
        src = f.read().replace('\r\n', '\n')
    for needle in [METHOD_START, METHOD_END, CONST_START, CONST_END] + CONSTANTS:
        if src.count(needle.lstrip('\n')) != 1:
            raise SystemExit('anchor not found exactly once in %s: %r' % (client_path, needle[:50]))
    consts = src[src.index(CONST_START):src.index(CONST_END) + len(CONST_END)]
    extra = '\n'.join(src[src.index(k):src.index(k) + len(k)] for k in CONSTANTS)
    body = src[src.index(METHOD_START):src.index(METHOD_END, src.index(METHOD_START))]
    return consts + '\n' + extra + '\n\n' + body


def main():
    client_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CLIENT_DIR
    src_root = os.path.join(client_dir, 'src', 'main', 'java')
    client = os.path.join(src_root, 'jagex2', 'client', 'Client.java')
    if not os.path.exists(client):
        raise SystemExit('no Client.java under %s' % src_root)
    with open(os.path.join(HERE, 'GroundItemsTest.shell.java')) as f:
        shell = f.read()
    work = tempfile.mkdtemp(prefix='groundtest')
    try:
        out = os.path.join(work, 'GroundItemsTest.java')
        with open(out, 'w') as f:
            f.write(shell.replace('__BODY__', extract(client)))
        # The whole client is compiled alongside, so the harness can drive the REAL
        # GroundItemPrefs against the real settings file rather than a stub of it.
        sources = []
        for root, _dirs, files in os.walk(src_root):
            sources += [os.path.join(root, n) for n in files if n.endswith('.java')]
        listing = os.path.join(work, 'sources.txt')
        with open(listing, 'w') as f:
            f.write('\n'.join(sources + [out]))
        r = subprocess.run(['javac', '-nowarn', '-encoding', 'UTF-8', '-d', work, '@' + listing],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            raise SystemExit('harness did not compile - the method changed shape')
        r = subprocess.run(['java', '-cp', work, 'GroundItemsTest'], capture_output=True, text=True,
                           cwd=work)   # DevLog writes dev-client.log into cwd; keep it in the temp dir
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
