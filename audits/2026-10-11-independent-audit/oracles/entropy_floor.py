#!/usr/bin/env python3
"""The floor, computed from a report instead of reconstructed from a document.

REPAIR-STRATEGY.md's "The floor, as arithmetic" states what to subtract from a
reported min-entropy figure to get a defensible lower bound. Until now it was
arithmetic in a document, which means someone in January has to (a) find the
right field in the report, (b) remember which terms apply, and (c) do it by
hand. Two of those three are recorded defects of this project:

  C02   the per-bit figure is h' = min(H_bitstring, H_original / word_size).
        The JSON's hOriginal is PER SYMBOL and the -c path's hAssessed is
        word_size * h'. Reading either as the per-bit figure is wrong by up to
        a factor of 8. This script reads the fields and shows which binds.
  C22   the P_local term is 8.08e-15 * (N+1), which nobody computes in their
        head, and the ZALPHA term has two readings whose difference matters.

So the floor is computed here, from the report, with every term named and its
source cited. Chosen as the most valuable remaining software item (OC-33):
every measurement in this audit exists to support this one number, and the
number was the only thing still produced by hand.

WHAT THIS REFUSES TO DO

  * It will not read a report with errorLevel != 0, or one carrying
    reportComplete: false (the C14 placeholder: the run did not finish).
  * It will not use hAssessed. If the report has one, it says why.
  * It will not extrapolate the ZALPHA term below 1,000,000 bits.
  * It says nothing about the restart decision (C23): that is a separate
    accept/reject computed by oracles/restart_decision_exact.py, and a figure
    is only awarded if that decision ACCEPTS. It is not a subtraction.
  * It establishes nothing about build provenance. A figure from a binary whose
    identity is unknown is uninterpretable regardless of this arithmetic
    (XR-04, XR-08, XR-09); run tools/build-provenance-canary.sh.

Usage:  entropy_floor.py <ea_non_iid report.json> [...]
        entropy_floor.py --from-log <ea_non_iid -vv output> [...]
        entropy_floor.py --manual <h_prime_per_bit> <bitstring_length_n>

--from-log exists to recompute figures that were produced BY HAND from a -vv
text log before this script existed, so the hand arithmetic can be checked by
the thing that replaced it (OC-37). Every read in it is anchored to its printed
LABEL, never to a line number or an ordinal: a missing label is an error, not a
fallback to position (OC-36's second rule). That is the other half of the bug
this script shipped with -- reading testCases[0] instead of the case labelled
Overall.
"""
import json, sys, os

# ---- the terms, each with the measurement that fixes it -------------------
C01 = 3.69e-4          # two-sided last-digit comparison error, measured bound (REPAIR-STRATEGY Class 2)
C22A_PER_N = 8.08e-15  # P_local bisection quantisation: half-ULP of x amplified by (N+1)  (OC-22)
C22B = 0.0             # P_global' at/near N == 1: conservative at every N, nothing to subtract (OC-22)
# ZALPHA versus the literal 2.576 (OC-22). Measured at two bitstring lengths;
# the ceiling DECREASES with n (dX' ~ sigma_max/sqrt(v), v ~ n/6), so the value
# measured at the largest n not exceeding the actual n is an upper bound.
C22C_BY_N = ((8_000_000, 2.16e-3), (1_000_000, 3.36e-3))

def c22c(n):
    for n0, b in C22C_BY_N:
        if n >= n0:
            return b, n0
    return None, None

def h_prime(report_path):
    """Return (h_prime_per_bit, n_bitstring, notes) read from an ea_non_iid report."""
    notes = []
    d = json.load(open(report_path))
    if d.get('reportComplete') is False:
        raise SystemExit("REFUSED: %s carries reportComplete: false -- the run did not finish "
                         "(the C14 placeholder). There is no figure to floor." % report_path)
    if d.get('errorLevel') not in (0, None):
        raise SystemExit("REFUSED: %s has errorLevel %r. A figure from a failed run has no floor."
                         % (report_path, d.get('errorLevel')))
    if d.get('IID') is True:
        notes.append("the report is from the IID track; C03's track-selection gap is UNBOUNDABLE "
                     "and is excluded from the floor only because the repair branch closed it. "
                     "Confirm the binary carries that repair (d226f18 or later).")
    # A non-IID report carries ONE TEST CASE PER ESTIMATOR, and the final
    # figures are in the one labelled "Overall" -- the minimum over estimators.
    # The first version of this script read testCases[0], the Most Common Value
    # estimator, and produced a floor from the wrong figure: 0.983 instead of
    # 0.904 on an 8-bit control, because Compression binds and MCV does not.
    # That is the same reading trap C02 names, one field over, and it is why
    # the case is selected by name and nothing else.
    cases = d.get('testCases') or []
    overall = [c for c in cases if (c.get('testCaseDesc') or '').strip().lower() == 'overall']
    if not overall:
        raise SystemExit("REFUSED: %s has no test case labelled 'Overall'. The per-estimator cases "
                         "are not the assessment; %d cases present: %s"
                         % (report_path, len(cases),
                            ", ".join((c.get('testCaseDesc') or '?') for c in cases)))
    if len(overall) > 1:
        raise SystemExit("REFUSED: %s has %d cases labelled 'Overall'." % (report_path, len(overall)))
    tc = overall[0]
    notes.append("read the 'Overall' case (the minimum over estimators), not any single "
                 "estimator's; the report carries %d cases." % len(cases))
    w = d.get('bitsPerSymbol')
    if not w:
        raise SystemExit("REFUSED: %s records no bitsPerSymbol, so a per-bit figure cannot be derived."
                         % report_path)
    if d.get('bitsPerSymbolInferred'):
        notes.append("bitsPerSymbol was INFERRED from the data, not given on the command line; "
                     "an inferred width can change which estimators ran.")
    if 'hAssessed' in tc:
        notes.append("the report carries hAssessed = %.17g. NOT USED as the per-bit figure: it is "
                     "word_size * h' (C02)." % tc['hAssessed'])
    h_orig = tc.get('hOriginal')
    h_bits = tc.get('hBitstring')
    if h_orig is None:
        raise SystemExit("REFUSED: %s has no hOriginal." % report_path)
    cand = [("H_original / word_size", h_orig / w)]
    if h_bits is not None:
        cand.append(("H_bitstring", h_bits))
    elif w > 1:
        notes.append("no hBitstring in the report for a %d-bit symbol; the bitstring pass may not "
                     "have run (-a / alphabet gate). h' rests on H_original / word_size alone." % w)
    binder, hp = min(cand, key=lambda t: t[1])
    # C02, checked rather than asserted: hAssessed should be exactly word_size * h'.
    ha = tc.get('hAssessed')
    if ha is not None:
        want = w * hp
        if abs(ha - want) > 1e-12 * max(1.0, abs(want)):
            notes.append("hAssessed %.17g is NOT word_size * h' (%.17g). The C02 relation does not "
                         "hold on this report, so one of the two readings is wrong -- stop and "
                         "resolve it before using either." % (ha, want))
        else:
            notes.append("consistency: hAssessed == word_size * h' to within 1e-12 relative, "
                         "as C02 describes.")
    n = int(d.get('assessedSampleCount') or 0) * w
    return hp, n, binder, cand, notes, d, tc

def from_log(path):
    """Read h', n and the symbol width from an ea_non_iid -vv text log, by label."""
    notes = []
    text = open(path, errors='replace').read()
    def labelled(pattern, what):
        import re
        m = re.search(pattern, text, re.M)
        if not m:
            raise SystemExit("REFUSED: %s has no line labelled %s. This reader is label-anchored: "
                             "a missing label is an error, never a fallback to a line number or an "
                             "ordinal (OC-36)." % (path, what))
        return m
    import re
    if re.search(r'^Usage is:', text, re.M):
        raise SystemExit("REFUSED: %s is a usage message, not an assessment. The tool did not run "
                         "on any data (OC-36's absence rule)." % path)
    m = labelled(r'^Loaded\s+(\d+)\s+samples of\s+(\d+)\s+distinct\s+(\d+)-bit-wide symbols',
                 "'Loaded N samples of K distinct W-bit-wide symbols'")
    samples, _k, w = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h_orig = float(labelled(r'^H_original\s*=\s*([0-9.eE+-]+)\s*$', "'H_original ='").group(1))
    mb = re.search(r'^H_bitstring\s*=\s*([0-9.eE+-]+)\s*$', text, re.M)
    cand = [("H_original / word_size", h_orig / w)]
    if mb:
        cand.append(("H_bitstring", float(mb.group(1))))
    elif w > 1:
        notes.append("no 'H_bitstring =' line for a %d-bit symbol; the bitstring pass did not run "
                     "(-a / alphabet gate). h' rests on H_original / word_size alone." % w)
    binder, hp = min(cand, key=lambda t: t[1])
    # The tool also prints the assessed figure; check it against h' as C02 describes.
    ma = re.search(r'^Assessed min entropy:\s*([0-9.eE+-]+)\s*$', text, re.M)
    if ma:
        a = float(ma.group(1))
        if abs(a - w * hp) <= 1e-12 * max(1.0, abs(w * hp)):
            notes.append("consistency: the printed 'Assessed min entropy' %.17g == word_size * h', "
                         "as C02 describes (it is per symbol, not per bit)." % a)
        elif abs(a - hp) <= 1e-12 * max(1.0, abs(hp)):
            notes.append("the printed 'Assessed min entropy' %.17g equals h' itself (1-bit data)." % a)
        else:
            notes.append("the printed 'Assessed min entropy' %.17g is neither h' nor word_size * h' "
                         "(%.17g) -- stop and resolve which figure is which before using either."
                         % (a, w * hp))
    notes.append("read from a -vv text log by label: width %d, %d samples." % (w, samples))
    return hp, samples * w, binder, cand, notes

def report(hp, n, binder=None, cand=None, notes=(), src=""):
    print("=" * 78)
    print(src)
    print("=" * 78)
    if cand:
        for name, v in cand:
            print("  %-26s %.17g %s" % (name, v, "<- binds" if name == binder else ""))
    print("  h' (per bit)               %.17g" % hp)
    print("  n (bitstring length)       %d bits" % n)
    for t in notes:
        print("  NOTE: %s" % t)
    if n < 1_000_000:
        raise SystemExit("REFUSED: n = %d is below the 1,000,000 bits the ZALPHA term was measured "
                         "at; this script will not extrapolate. Run OC-22's harness at this n." % n)
    bz, bz_n = c22c(n)
    a = C22A_PER_N * (n + 1)
    print()
    print("  term                                     value        why")
    print("  ---------------------------------------- ------------ " + "-" * 34)
    print("  C01 comparison error                     %.3e    measured two-sided bound" % C01)
    print("  C22a P_local quantisation                %.3e    8.08e-15 x (n+1), n = %d" % (a, n))
    print("  C22b P_global' at N == 1                 %.3e    conservative at every N" % C22B)
    print("  C22c ZALPHA vs the literal 2.576         %.3e    measured at n = %d (ceiling falls with n)" % (bz, bz_n))
    lit = hp - C01 - a - C22B - bz
    f07 = hp - C01 - a - C22B
    print()
    print("  FLOOR, literal-text reading   %.17g   (h' - %.6g)" % (lit, hp - lit))
    print("  FLOOR, F07 reading            %.17g   (h' - %.6g)" % (f07, hp - f07))
    print("    F07 is this audit's own disposition: the tool uses the exact 0.995 quantile and the")
    print("    standard's text prints its rounding, so C22c is a literal-text parity term, not a defect.")
    print()
    print("  EXCLUDED, not subtracted:")
    print("    C07, C03  closed by code on master at d226f18 and later. For a figure from tag")
    print("              unrepaired-reference-2026-10-15 the exclusion does NOT hold and no floor exists.")
    print("    C02       a reading, not a subtraction: this script used h', never hAssessed.")
    print("  SEPARATE, not a subtraction:")
    print("    C23       the restart sanity check is an accept/reject decision, recomputed with")
    print("              oracles/restart_decision_exact.py. A figure is awarded only if it ACCEPTS.")
    print("              The printed 3.1.4.3 binomial formula must NOT be used for it (OC-30).")
    print("  NOT ESTABLISHED HERE:")
    print("    build provenance -- run tools/build-provenance-canary.sh. A figure from an")
    print("    unidentified binary is uninterpretable whatever this arithmetic says.")
    print("    The repairs these exclusions rest on are self-authored and UNREVIEWED.")
    print()

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    if args[0] == '--from-log':
        for path in args[1:]:
            hp, n, binder, cand, notes = from_log(path)
            report(hp, n, binder, cand, notes, src="%s  (-vv text log)" % os.path.basename(path))
        sys.exit(0)
    if args[0] == '--manual':
        if len(args) != 3:
            raise SystemExit("usage: entropy_floor.py --manual <h_prime_per_bit> <n_bits>")
        report(float(args[1]), int(args[2]), src="manual: h' and n supplied on the command line")
    else:
        for path in args:
            hp, n, binder, cand, notes, d, tc = h_prime(path)
            report(hp, n, binder, cand, notes, src="%s  (%s, %s)" % (
                os.path.basename(path), d.get('type', '?'), d.get('toolVersion', '?')))
