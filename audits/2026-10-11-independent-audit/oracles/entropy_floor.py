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
# C01 / F10 -- A02, AND THE LABEL WAS WRONG TWICE (OC-55).
#
# This term was described as a "two-sided last-digit comparison error, measured
# bound". Both halves were wrong. The 3.69e-4 figure comes from F10:
# MultiMMC's CHAINED PREFIX LOOKUP under the MAX_ENTRIES cap
# (multi_mmc_test.h:236/:93). SP 800-90B 6.3.9 step 4.b.i requires an
# independent lookup of M_d at every depth; the code looks up depth d only if
# depth d-1 hit, and when the cap refuses a prefix entry at depth d every later
# recurrence of that context suppresses all depth >= d predictions. The size of
# that effect is set by HOW THE DICTIONARY FILLS, which is a property of the
# data. Nothing in a rounding argument constrains it, so 3.69e-4 is ONE
# MEASUREMENT and not a bound -- exactly as the outside audit said.
#
# OF THE THREE OPTIONS (prove a bound, correct the algorithm, exclude the
# affected path) THIS TAKES THE THIRD, and for width 1 the exclusion is a
# PROOF rather than a judgement:
#
#   D_MMC = 16 and MAX_ENTRIES = 100000 (multi_mmc_test.h:4-5). The loop runs
#   d = 0..15. For BINARY data, depth d has at most 2^(d+1) distinct prefixes
#   and at most 2 postfixes each, so entries[d] <= 2^(d+2).
#     d <= 14:  2^16 = 65536 < 100000  -- the cap CANNOT bind.
#     d  = 15:  2^17 = 131072 > 100000 -- the cap can bind, but d = 15 is the
#               TOP depth and the defect needs a depth d+1 to suppress.
#   So at width 1 no suppression is reachable and F10 cannot move the figure.
#
# For width > 1 the cap does bind below the top depth and the term stays, but
# it is an EVALUATED MARGIN over the inputs measured, not a certified bound,
# and the output says so. Correcting the algorithm is the second option and is
# a change to estimator numerics, which is the owner's call, not this script's.
C01 = 3.69e-4          # F10 margin; EXCLUDED at width 1 by the proof above (A02 / OC-55)
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
    # ========================================================================
    # VALIDATE THE EVIDENCE BEFORE EMITTING ANYTHING (A08).
    #
    # An outside audit handed this script four reports and got a FLOOR and exit
    # 0 from all four: one with no errorLevel at all, one with
    # nonCompliantShortDataset true, one claiming 10 bits of entropy per
    # ONE-BIT sample, and one carrying a nonfinite value that Python's parser
    # accepts by default. Reproduced exactly. It is the
    # compared-nothing-and-exited-zero shape, in the tool built to audit the
    # tool, which is worse than finding it in the tool.
    #
    # The errorLevel case is the sharpest, because the old test was
    #     if d.get('errorLevel') not in (0, None)
    # which reads a MISSING field as acceptable -- a conclusion from absence,
    # the thing this project's own constraints forbid. Absence of a field is
    # not evidence that the field's condition held.
    # ========================================================================
    def _nonfinite(tok):
        raise SystemExit("REFUSED: %s contains the JSON token %r. NaN and Infinity are not "
                         "numbers a min-entropy report can carry, and Python's parser accepts "
                         "them silently by default. Nothing is floored from a report with a "
                         "nonfinite value in it." % (report_path, tok))
    with open(report_path) as fh:
        d = json.load(fh, parse_constant=_nonfinite)
    if not isinstance(d, dict):
        raise SystemExit("REFUSED: %s is not a JSON object, so it is not a report." % report_path)
    # the schema this reader depends on, required by NAME and not by position
    for k in ('type', 'toolVersion', 'errorLevel', 'testCases', 'bitsPerSymbol'):
        if k not in d:
            raise SystemExit("REFUSED: %s has no %r. This reader is schema-anchored: a document "
                             "missing a required field is an unrecognised document, not a report "
                             "with a default (A08)." % (report_path, k))
    if d.get('reportComplete') is False:
        raise SystemExit("REFUSED: %s carries reportComplete: false -- the run did not finish "
                         "(the C14 placeholder). There is no figure to floor." % report_path)
    if d.get('errorLevel') != 0:
        raise SystemExit("REFUSED: %s has errorLevel %r, not 0. A figure from a failed run has no "
                         "floor." % (report_path, d.get('errorLevel')))
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
    # A08: a short dataset is not a compliant assessment, whichever case flags it.
    flagged = [ (c.get('testCaseDesc') or '?') for c in cases
                if c.get('nonCompliantShortDataset') is True ]
    if d.get('nonCompliantShortDataset') is True or flagged:
        raise SystemExit("REFUSED: %s is flagged nonCompliantShortDataset%s. The assessment does "
                         "not meet the standard's sample-count requirement, so there is no "
                         "compliant figure to floor." % (report_path,
                         (" on: " + ", ".join(flagged)) if flagged else ""))
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
    # A08, AND THE FIRST THING THAT SHOULD BE REFUSED. Min-entropy per symbol
    # cannot exceed the symbol's width: 10 bits from a one-bit sample is
    # impossible on its face, and the old script printed a floor of 9.996 bits
    # for exactly that report. A figure that violates its own units needs no
    # further analysis.
    for name, val, ceiling in (('hOriginal', h_orig, float(w)),
                               ('hAssessed', tc.get('hAssessed'), float(w)),
                               ('hBitstring', h_bits, 1.0)):
        if val is None:
            continue
        if not isinstance(val, (int, float)) or val != val or val in (float('inf'), float('-inf')):
            raise SystemExit("REFUSED: %s has a %s that is not a finite number (%r)."
                             % (report_path, name, val))
        if val < 0.0:
            raise SystemExit("REFUSED: %s has %s = %.17g, which is negative. Min-entropy cannot be."
                             % (report_path, name, val))
        if val > ceiling:
            raise SystemExit("REFUSED: %s has %s = %.17g for a %d-bit symbol, which exceeds the "
                             "%g-bit ceiling that unit allows. A report that contradicts its own "
                             "units is not floored, it is rejected (A08)."
                             % (report_path, name, val, w, ceiling))
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
    return hp, n, binder, cand, notes, d, tc, w

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
    return hp, samples * w, binder, cand, notes, w

def report(hp, n, binder=None, cand=None, notes=(), src="", w=None):
    # A02: the width decides whether C01/F10 is reachable at all, so it is a
    # required input to the report rather than something inferred here. None
    # means "not established", and then nothing is called a floor.
    if w is None:
        raise SystemExit("REFUSED: the bit width was not established, so whether the C01/F10 "
                         "term is reachable cannot be decided and no floor can be claimed (A02).")
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
    if w == 1:
        print("  C01/F10 MultiMMC chained lookup          %.3e    EXCLUDED: unreachable at width 1" % 0.0)
        print("    D_MMC=16, MAX_ENTRIES=100000; for binary data entries[d] <= 2^(d+2), so the cap")
        print("    cannot bind below d=15 and d=15 has no d+1 to suppress. A proof, not a measurement.")
    else:
        print("  C01/F10 MultiMMC chained lookup          %.3e    EVALUATED MARGIN, *not* a bound" % C01)
        print("    One measured overestimate from f10_over_8bit_1M. The mechanism is dictionary")
        print("    saturation, whose size is set by the data, so nothing here constrains it (A02).")
    print("  C22a P_local quantisation                %.3e    8.08e-15 x (n+1), n = %d" % (a, n))
    print("  C22b P_global' at N == 1                 %.3e    conservative at every N" % C22B)
    print("  C22c ZALPHA vs the literal 2.576         %.3e    derived ceiling, at n = %d" % (bz, bz_n))
    print("    The binding estimator is COMPRESSION (bitstring), whose com_exp is stationary at")
    print("    p = 1/64 so the sensitivity is quadratic on the approach to its cap. Reproduced")
    print("    independently where it can be: num_blocks and dX' to three significant figures,")
    print("    and the collision family's whole ceiling to 0.07% (OC-62). Its fall with n is")
    print("    measured, not asserted: oracles/zalpha_ceiling_by_n.py.")
    # A02: C01 is excluded at width 1 by proof, and is a MARGIN above it.
    c01 = 0.0 if w == 1 else C01
    certified = (w == 1)
    lit = hp - c01 - a - C22B - bz
    f07 = hp - c01 - a - C22B
    print()
    # "CERTIFIED FLOOR" and "EVALUATED MARGIN" are different claims and the
    # output must not blur them (A02). A floor is claimed only when every
    # subtracted term is a bound over the supported inputs.
    # EACH READING IS LABELLED ON ITS OWN TERMS (OC-59). A reading is a
    # CERTIFIED FLOOR only when EVERY term it subtracts is a bound over the
    # supported inputs. Two things disqualify a term:
    #   * C01/F10 above width 1 -- an evaluated margin, mechanism data-dependent
    #     (A02 / OC-55);
    #   * C22c at ANY width -- the tabulated 3.36e-3 / 2.16e-3 are NOT
    #     reproduced by an independent derivation of the binding family, which
    #     gives 7.49e-4 / 4.46e-4 (OC-59). The discrepancy is in the safe
    #     direction, so the figure is not overstated, but an unreproduced
    #     subtrahend is not a bound and must not be called one.
    # The LITERAL reading subtracts C22c; the F07 reading does not. So at width
    # 1 the F07 reading is a certified floor and the literal reading is not --
    # labelling the whole report with one word would have blurred exactly the
    # distinction this oracle exists to keep.
    # OC-62 CORRECTS OC-59. C22c IS a bound: a ceiling derived from dz, the
    # estimator's cap, n, Popoviciu's sigma_max and v >= n/3 -- not an observed
    # maximum. OC-59 reported it as unreproduced because the derivation it
    # compared against computed the COLLISION family, while the tabulated term
    # is the COMPRESSION ceiling, which is 4.3-4.6x larger. The "unexplained"
    # ratio was simply compression/collision. Both families now reproduce the
    # record where they can be checked independently
    # (oracles/zalpha_ceiling_by_n.py), so the literal reading is a certified
    # floor again wherever C01/F10 is also excluded.
    lit_terms_all_bounds = certified
    f07_terms_all_bounds = certified
    lab_lit = "CERTIFIED FLOOR" if lit_terms_all_bounds else "EVALUATED MARGIN (not a floor)"
    lab_f07 = "CERTIFIED FLOOR" if f07_terms_all_bounds else "EVALUATED MARGIN (not a floor)"
    print("  %-31s %.17g   (h' - %.6g)" % (lab_lit + ", literal", lit, hp - lit))
    print("  %-31s %.17g   (h' - %.6g)" % (lab_f07 + ", F07", f07, hp - f07))
    if not certified:
        print("    NOT A FLOOR: the C01/F10 term above is an evaluated margin over the inputs")
        print("    measured, not a bound over all accepted ones. Treat this as a working figure")
        print("    and do not publish it as a floor until F10 is repaired or bounded (A02).")
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
            hp, n, binder, cand, notes, w = from_log(path)
            report(hp, n, binder, cand, notes, src="%s  (-vv text log)" % os.path.basename(path), w=w)
        sys.exit(0)
    if args[0] == '--manual':
        if len(args) != 3:
            raise SystemExit("usage: entropy_floor.py --manual <h_prime_per_bit> <n_bits>")
        report(float(args[1]), int(args[2]), src="manual: h' and n supplied on the command line")
    else:
        for path in args:
            hp, n, binder, cand, notes, d, tc, w = h_prime(path)
            report(hp, n, binder, cand, notes, w=w, src="%s  (%s, %s)" % (
                os.path.basename(path), d.get('type', '?'), d.get('toolVersion', '?')))
