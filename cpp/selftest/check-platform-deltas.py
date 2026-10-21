#!/usr/bin/env python3
"""Decide whether a failing selftest is covered by the known-platform-delta
exception (A06 / OC-56).

Reads selftest's output on stdin and the manifest named by
SELFTEST_DELTA_MANIFEST. Exits 0 only when ALL of the following hold:

  1. a `platform` block in the manifest matches this host -- uname -s, uname -m
     and a substring of the compiler identity (PLAT_S / PLAT_M / PLAT_CC);
  2. every reported difference matches a `delta` row for that platform on
     file, estimator and field, and its |delta| is within the row's tolerance;
  3. every `delta` row for that platform was actually observed.

Rule 3 is there because a comparison that silently stopped happening must not
pass as an absence of difference -- the same shape as the empty-classification
failure this harness already guards against.

THE TOLERANCES ARE MEASURED MAGNITUDES WITH HEADROOM, NOT BOUNDS. Nothing here
proves a platform delta cannot exceed its row; the rows record what was
observed, with room above it. That is why a delta over its row is reported as a
FINDING rather than as a reason to widen the row (rule 6: an observed maximum
is not a bound).

The old exception was a list of two FILENAMES and inspected nothing else, so a
deliberate change from 0.85 to 0.01 in one of those files was accepted.
"""
import os, re, sys

# NOT ANCHORED AT THE LINE START. selftest prints the first difference for a
# file on the same line as the filename ("ringOsc-nist.bin: ringOsc-nist.res:
# Significant difference for ..."), and the first version of this anchored with
# ^ and so silently skipped exactly those lines -- then reported them as
# MISSING comparisons, which is the right verdict for the wrong reason and
# would have read as "the comparison stopped happening". Search instead, and
# take the .res name nearest the phrase.
DIFF = re.compile(
    r'(?P<file>[^\s:]+\.res):\s*Significant difference for\s+(?P<est>.+?):\s*'
    r'(?P<field>.+?)\s*\(reference:\s*(?P<ref>[-0-9.eE+]+)\s+new:\s*(?P<new>[-0-9.eE+]+)'
    r'\s+delta:\s*(?P<delta>[-0-9.eE+]+)\)')

def load(path, s, m, cc):
    blocks, cur = [], None
    try:
        text = open(path).read()
    except OSError as e:
        print("REFUSED: cannot read the delta manifest %s (%s)" % (path, e)); sys.exit(2)
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        if ln.startswith('platform '):
            parts = ln.split(None, 3)
            if len(parts) < 4:
                print("REFUSED: malformed platform line: %s" % ln); sys.exit(2)
            cur = {'s': parts[1], 'm': parts[2], 'cc': parts[3], 'rows': {}}
            blocks.append(cur)
        elif ln.startswith('delta '):
            if cur is None:
                print("REFUSED: a delta row appears before any platform line"); sys.exit(2)
            body = ln[len('delta '):]
            f = body.split('|')
            if len(f) != 4:
                print("REFUSED: malformed delta row: %s" % ln); sys.exit(2)
            try:
                tol = float(f[3])
            except ValueError:
                print("REFUSED: malformed tolerance in: %s" % ln); sys.exit(2)
            cur['rows'][(f[0].strip(), f[1].strip(), f[2].strip())] = tol
        else:
            print("REFUSED: unrecognised manifest line: %s" % ln); sys.exit(2)
    for b in blocks:
        if b['s'] == s and b['m'] == m and b['cc'] in cc:
            return b
    return None

def main():
    path = os.environ.get('SELFTEST_DELTA_MANIFEST', 'known-platform-deltas.txt')
    s, m, cc = os.environ.get('PLAT_S',''), os.environ.get('PLAT_M',''), os.environ.get('PLAT_CC','')
    blk = load(path, s, m, cc)
    seen, problems = {}, []
    for ln in sys.stdin.read().splitlines():
        mt = DIFF.search(ln.strip())
        if not mt:
            continue
        key = (mt.group('file').replace('.res', '.bin'), mt.group('est').strip(), mt.group('field').strip())
        try:
            d = abs(float(mt.group('delta')))
        except ValueError:
            problems.append("unparseable delta in: %s" % ln.strip()); continue
        seen[key] = max(d, seen.get(key, 0.0))

    if blk is None:
        print("the exception does NOT apply on this platform: no manifest block matches")
        print("  uname -s = %s   uname -m = %s" % (s, m))
        print("  compiler = %s" % cc)
        print("  a familiar filename is not a reason to excuse a difference on an")
        print("  unlisted platform; add a block with measured rows, or fix the difference.")
        sys.exit(1)

    for key, d in sorted(seen.items()):
        tol = blk['rows'].get(key)
        if tol is None:
            problems.append("UNEXPECTED difference, no manifest row: %s | %s | %s  (delta %.6g)" % (key + (d,)))
        elif d > tol:
            problems.append("delta TOO LARGE: %s | %s | %s  delta %.6g > tolerance %.6g"
                            % (key + (d, tol)))
    for key in sorted(blk['rows']):
        if key not in seen:
            problems.append("MISSING comparison, a listed row was never reported: %s | %s | %s" % key)

    if problems:
        print("the platform-delta exception does NOT cover this run:")
        for p in problems:
            print("  - %s" % p)
        sys.exit(1)
    print("%d expected platform delta(s), all within tolerance, on %s %s "
          "(tolerances are measured magnitudes with headroom, not bounds)" % (len(seen), s, m))
    sys.exit(0)

if __name__ == '__main__':
    main()
