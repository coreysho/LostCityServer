#!/usr/bin/env python3
"""
Runs the headless harness for the left-click swapper.

MenuSwaps is tested as the real compiled class against the real swaps file - its job is
surviving disk, so a mock of the disk would test nothing. Client.applyMenuSwap() is
extracted out of Client.java every run, so the test exercises the source that ships rather
than a copy of it that can quietly drift.

    python3 run_swaptest.py [path\\to\\javaclient]

Needs javac/java on PATH. Compiles the whole client to a temp dir; nothing is left behind
except the swaps file the harness deletes itself.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLIENT_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'javaclient'))

METHOD_START = '\tprivate void applyMenuSwap() {'
METHOD_END = '\n\t/**\n\t * Turns the menu row the player just picked into a stored swap.'


def extract(client_java):
    with open(client_java, newline='') as f:
        src = f.read().replace('\r\n', '\n')
    for needle in (METHOD_START, METHOD_END):
        if src.count(needle.lstrip('\n')) != 1:
            raise SystemExit('anchor not found exactly once: %r' % needle[:60])
    start = src.index(METHOD_START)
    return src[start:src.index(METHOD_END, start)]


def main():
    client_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CLIENT_DIR
    src_root = os.path.join(client_dir, 'src', 'main', 'java')
    client_java = os.path.join(src_root, 'jagex2', 'client', 'Client.java')
    if not os.path.exists(client_java):
        raise SystemExit('no Client.java under %s' % src_root)
    with open(os.path.join(HERE, 'MenuSwapTest.shell.java')) as f:
        shell = f.read()

    work = tempfile.mkdtemp(prefix='swaptest')
    try:
        out = os.path.join(work, 'MenuSwapTest.java')
        with open(out, 'w') as f:
            f.write(shell.replace('__BODY__', extract(client_java)))
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
            raise SystemExit('harness did not compile')
        r = subprocess.run(['java', '-cp', work, 'MenuSwapTest'], capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
