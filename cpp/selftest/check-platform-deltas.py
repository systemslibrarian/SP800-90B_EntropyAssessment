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

# ===========================================================================
# F05 (OC-81) -- A FILTER REFUSES WHAT IT DOES NOT RECOGNISE.
#
# The loop below used to be:
#
#     mt = DIFF.search(ln.strip())
#     if not mt:
#         continue
#
# so every line selftest printed that was not a "Significant difference"
# matching this exact shape was SILENTLY DISCARDED. A difference reported in
# any other form -- a new diagnostic, a harness error, a comparison that
# announced it could not run -- left no trace, the recognised rows were all
# within tolerance, and this script printed "N expected platform delta(s), all
# within tolerance" and exited 0. --allow-known-platform-deltas is the
# documented macOS invocation, so that is the path normally run.
#
# The taxonomy below is MEASURED, not imagined. `./selftest` on this host emits
# 33 lines in exactly six shapes, and they are enumerated here; anything else
# is a diagnostic this script has never seen and must not judge.
BENIGN = [
    re.compile(r'^$'),
    # the fixture inventory, which also carries the reference COUNT used below
    re.compile(r'^fixture-inventory:\s'),
    # per-file comparison summary, including the identity limb compareresults.pl
    # asserts. If that limb ever said anything but "matched", the line stops
    # matching here and is refused as unrecognised, which is the correct
    # outcome: this script must not excuse a run whose inputs were not identified.
    re.compile(r'^(?P<res>[^\s:]+\.res):\s+\d+\s+value\(s\) compared;\s+identity\s+'
               r'\S+\s+/\s+\d+\s+samples\s+/\s+\d+-bit matched\s*$'),
    # the per-file and overall maximum-delta lines. BOTH EXTENSIONS ARE NAMED
    # because the per-file form carries the .bin name while the comparison
    # summary above carries the .res name -- and the taxonomy pass that built
    # this list normalised every filename to one token, which hid exactly that
    # distinction. The first draft accepted only .res and refused nine
    # legitimate lines. When measuring the shapes a filter must accept, do not
    # normalise away the part the filter keys on.
    re.compile(r'^([^\s:]+\.(?:bin|res):\s+)?Maximum delta:\s+[-0-9.eE+]+\s*$'),
    # the summary verdict
    re.compile(r'^selftest:\s+(PASS|FAIL)\b'),
]
COMPARED = BENIGN[2]
INVENTORY = re.compile(r'^fixture-inventory:\s+(?P<verdict>\S+)\s+\((?P<inputs>\d+)\s+inputs,\s+'
                       r'(?P<refs>\d+)\s+references;')
SUMMARY = re.compile(r'^selftest:\s+FAIL\s+\((?P<k>\d+)\s+of\s+(?P<n>\d+)\s+files\):\s*(?P<files>.*)$')


def main():
    path = os.environ.get('SELFTEST_DELTA_MANIFEST', 'known-platform-deltas.txt')
    s, m, cc = os.environ.get('PLAT_S',''), os.environ.get('PLAT_M',''), os.environ.get('PLAT_CC','')
    blk = load(path, s, m, cc)
    seen, problems = {}, []
    compared, inventory, summary = set(), None, None
    for ln in sys.stdin.read().splitlines():
        t = ln.strip()
        mt = DIFF.search(t)
        if mt:
            key = (mt.group('file').replace('.res', '.bin'), mt.group('est').strip(),
                   mt.group('field').strip())
            try:
                d = abs(float(mt.group('delta')))
            except ValueError:
                problems.append("unparseable delta in: %s" % t); continue
            seen[key] = max(d, seen.get(key, 0.0))
            continue
        cm = COMPARED.match(t)
        if cm:
            compared.add(cm.group('res').replace('.res', '.bin'))
            continue
        im = INVENTORY.match(t)
        if im:
            inventory = im
            continue
        sm = SUMMARY.match(t)
        if sm:
            summary = sm
            continue
        if any(b.match(t) for b in BENIGN):
            continue
        # NOT RECOGNISED. Refuse rather than discard: this script's whole
        # purpose is to decide whether a failing selftest is the KNOWN platform
        # difference, and it cannot decide that about output it cannot read.
        problems.append("UNRECOGNISED selftest output, refusing to judge this run: %s"
                        % (t if len(t) <= 160 else t[:157] + '...'))

    # ---- COMPLETENESS: the comparison set must be whole ----
    #
    # The old check required every manifest ROW to have been observed, which
    # catches a delta that stopped being reported. It did NOT catch a selftest
    # that compared fewer FILES than exist, because a file with no listed delta
    # row contributes no row to miss. selftest prints the reference count
    # itself, so completeness is checked against its own number rather than
    # against anything written here twice.
    if inventory is None:
        problems.append("no 'fixture-inventory:' line: the reference set was never declared, "
                        "so the comparison cannot be shown complete")
    else:
        if inventory.group('verdict') != 'PASS':
            problems.append("fixture-inventory did not PASS (%s): the references themselves are "
                            "in question, so no difference can be excused" % inventory.group('verdict'))
        nrefs = int(inventory.group('refs'))
        if len(compared) != nrefs:
            problems.append("INCOMPLETE comparison: %d reference(s) declared, %d file(s) actually "
                            "compared (%s)" % (nrefs, len(compared), ", ".join(sorted(compared)) or "none"))
        if summary is not None and int(summary.group('n')) != nrefs:
            problems.append("selftest's own summary counts %s files where the inventory declares %d"
                            % (summary.group('n'), nrefs))

    # ---- and the summary's file list must agree with the differences parsed ----
    #
    # This is the cross-check that makes the two readings verify each other: if
    # a difference were reported in a form the DIFF regex does not match, the
    # summary would name a file for which nothing was parsed. The unrecognised
    # -line refusal above should already have fired; this catches the case where
    # the line is benign-shaped but carries a verdict.
    if summary is not None:
        named = set(summary.group('files').split())
        parsed = {k[0] for k in seen}
        for f in sorted(named - parsed):
            problems.append("selftest names %s as differing, but no difference for it was parsed" % f)
        for f in sorted(parsed - named):
            problems.append("a difference was parsed for %s, which selftest's summary does not name" % f)

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
