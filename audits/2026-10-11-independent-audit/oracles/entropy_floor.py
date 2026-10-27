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

WHICH TERM IS WHICH SIZE, AND WHY THAT DECIDES WHERE SCRUTINY BELONGS

This was not written down anywhere until OC-125, and the omission had a
consequence. At width 1 and the 1,000,000 samples 3.1.1 requires as a minimum:

    term   value at n = 1e6     share of what is subtracted   status
    C22c   3.3599300e-3         99.99976 %                    DERIVED
    C22a   8.08e-9              0.00024 %                     MEASURED
    C22b   0                    0 %                           PROVED

C22c is FIVE ORDERS OF MAGNITUDE larger than C22a and is essentially the
entire subtraction. At n = 8e6 the ratio narrows to 33,484x and C22c is still
99.997 % of the total. The binding family inside C22c is COMPRESSION at both
lengths, 4.3x over the collision runner-up at n = 1e6 and 4.6x at n = 8e6.

AND THE SCRUTINY WENT THE OTHER WAY. C22a -- 0.00024 % of the subtraction --
received a grid-interiority argument, a nine-order refinement sweep, an
independent 80-digit solver, a withdrawn verification with its own register
entry, and a scan over the mathematically-defined r/N/k domain. C22c --
99.99976 % of it -- was a hand-typed constant that nothing compared against
the derivation that produced it, and a mutation of it left the oracles' own
selftest green. The relative magnitudes were never tabulated, so nobody could
see that the effort was inverted.

So the proportions live here now, beside the terms, where the next person
deciding what to examine will read them.

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
# P_local bisection quantisation: half-ULP of x amplified by (N+1) (OC-22).
#
# THE VALUE AND ITS SUPREMACY ARE BOTH ESTABLISHED (OC-63). The constant behind
# this term is a MAXIMUM OVER A GRID in oracles/p_local_exact.py, over four
# author-chosen axes, and rule 9 says a grid maximum is only a LOWER BOUND on
# the true extremum unless the argmax is shown interior -- so it was measured
# rather than assumed. The argmax is interior in every swept axis: N = 10,000
# (5th of 12) and r = 3 (2nd of 7), and extending the one remaining arbitrary
# axis -- the root-offset refinement window, 10^-12 to 10^-21, 592 near-root
# points to 1036 -- left the maximum BIT-IDENTICAL at 0.4991, same N, same r,
# same p. A maximum that does not move when its last arbitrary axis is extended
# nine orders is an interior maximum, so this is the SUPREMUM and
# eps_f <= c (N+1) 2^-52 is a bound.
#
# The superseded half of this comment -- "nothing checks that the maximum is
# interior, so by rule 9 it is a LOWER BOUND ... settling it means extending
# each arbitrary axis" -- was left beneath the headline when OC-63 was written,
# so this file asserted both that the term is a bound and that it is not, while
# execution took the established path. Removed (OC-73): the printed labels were
# current and the file's own reasoning contradicted them.
C22A_PER_N = 8.08e-15
#
# THE PER-TERM STATUS VOCABULARY (F02). Three statuses, and the floor takes the
# WEAKEST of its terms, because a certified claim resting on an uncertified
# input is not certified:
#
#   PROVED    holds for every input in the supported domain by an argument.
#   DERIVED   follows from a PROVED inequality evaluated at numerical inputs.
#   MEASURED  a maximum over an author-chosen grid or scan. Rule 9 governs it:
#             such a maximum is a LOWER BOUND on the true extremum unless the
#             argmax is shown interior, and "shown interior" is evidence about
#             the rows sampled, not a proof.
#
# C22a IS MEASURED, AND THIS FILE USED TO LIST IT AMONG THE BOUNDS. The exact
# sentence was "every term is now a bound at width 1: C01/F10 excluded by
# proof, C22a a measured supremum, C22b zero, C22c a derived ceiling" -- a
# measured supremum named as such inside a list of bounds. F02 is right.
#
# And the reproduction is worse than the finding. The subtracted constant is a
# PRODUCT OF TWO GRID MAXIMA, and OC-63's interiority argument covers only the
# first:
#   c    = 0.4991      max |f_tool - f_exact| / ((N+1) 2^-52) over 592 near-root
#                      points; argmax at N = 10,000, r = 3, INTERIOR, and
#                      bit-identical when the refinement window is extended nine
#                      orders (OC-63). This factor's status is as good as a
#                      measurement gets.
#   K    = 1.6189e-14  sup over the (N, r, ldomain) sweep of
#                      2^-52/(|f'(p*)| p* ln 2), attained at N = 5, r = 2 --
#                      and r = 2 IS THE FIRST VALUE IN THE SWEPT LIST
#                      [2, 3, 4, 5, 6, 8, ...]. K is largest where |f'(p*)| p*
#                      is smallest, the script's own model puts that minimum at
#                      r = 2, and whether the true infimum lies at r = 2 or at
#                      r = 1 (which the standard admits when the longest run of
#                      correct predictions is 0) WAS NEVER EXAMINED. Rule 9
#                      applies to this factor and was never applied to it.
# 8.08e-15 = c * K. Declaring the PRODUCT a bound on the strength of an
# interiority argument for ONE factor is the gap.
#
# And the margin is thin: the sweep's own worst realised inflation reaches
# 92.8% of the ceiling it is supposed to bound (0.463 realised against
# c = 0.499). A grid maximum that its own grid approaches to within 7.2% is not
# a comfortable bound.
#
# Reproduced 2026-10-21 by oracles/p_local_exact.py against a c22_bound built
# from production headers at sha256 9619117ec68ee3fe.
#
# THIS IS A WITHDRAWN VERIFICATION, NOT ONLY A RELABEL. OC-63 claimed the
# constant had been VERIFIED to be a supremum; that claim is withdrawn, with
# its date and reason, as WV-2 in audits/WITHDRAWN-VERIFICATIONS.md. The
# register exists because a withdrawal recorded only in the entry that
# performed it is a withdrawal nobody finds -- and because two were withdrawn
# in the same week (WV-1 is C23's cutoff check, printed from an empty loop).
C22B = 0.0             # P_global' at/near N == 1: conservative at every N, nothing to subtract (OC-22)
# ZALPHA versus the literal 2.576 (OC-22). Measured at two bitstring lengths;
# the ceiling DECREASES with n (dX' ~ sigma_max/sqrt(v), v ~ n/6), so the value
# measured at the largest n not exceeding the actual n is an upper bound.
# SHAPE-07 APPLIED HERE (OC-67). C22c is a MAX OVER ESTIMATOR FAMILIES, and it
# used to be stored as that maximum alone. The components were discarded, and
# that is exactly how OC-59 happened: I derived the Collision family, compared
# it against this number, found a consistent 4.5x gap and reported the RECORD as
# unreproduced -- when the number is the COMPRESSION ceiling and Collision is
# 4.3-4.6x smaller. The aggregate had hidden which family bound.
#
# So the components are carried, the binding one is named, and the margin to
# the runner-up is kept. A figure whose binding family cannot be identified
# cannot be audited by anyone, including me next month.
#
# Values from OC-22 Part 3; reproduced independently where checkable by
# oracles/zalpha_ceiling_by_n.py (OC-62).
#
# THE COMPRESSION CEILING IS NOW INDEPENDENTLY DERIVED, AND CARRIED TO FIVE
# FIGURES (OC-86). It used to be stored as 3.36e-3 / 2.16e-3, the three-figure
# values the record tabulated from production's 801-point scan -- and it was the
# one quantity in C22c that NOTHING outside production had ever computed:
# zalpha_ceiling_by_n.py printed "(production solve, not reimplemented here)"
# for exactly these two cells, which are the cells this file subtracts.
#
# oracles/compression_ceiling_exact.py now computes it from SP 800-90B 6.3.4
# step 7 as written, validated against the standard's OWN worked example
# (d=4, N=8, v=4, X'=1.4617 -> NIST publishes p = 0.5715; the file gets
# 0.57148426). It agrees with production's scan to six and seven significant
# figures respectively, and the cap com_exp(2^-6) agrees to sixteen.
#
# Five figures, not three, because at n = 8e6 the three-figure rounding
# discarded 4.4e-6 bit -- 88% of what three figures permits -- in the direction
# of subtracting too LITTLE. The extra digits cost nothing and drop the
# comparison tolerance from 0.231% to 0.0023%.
# =============================================================================
# THE VALUES ARE NO LONGER WRITTEN HERE (OC-125). THIS WAS THE DEFECT.
#
# Until this commit the six family ceilings were literals in this file:
#
#     C22C_FAMILIES_BY_N = (
#         (8_000_000, {'compression': 2.1644e-3, 'collision': 4.66e-4, ...}),
#         (1_000_000, {'compression': 3.3599e-3, 'collision': 7.84e-4, ...}),
#     )
#
# and compression_ceiling_exact.py carried a SECOND copy of the compression
# pair, which it compared against its own fresh derivation of 6.3.4 step 7.
# So the value that was VERIFIED and the value that was SUBTRACTED were
# different objects, and nothing joined them. Measured twice: mutating the copy
# above, 3.3599e-3 -> 3.3700e-3, left oracle-selftest GREEN -- once as OC-105,
# and again when the band-1 battery re-ran both C22c arms on 2026-10-26 and
# reported NOT CAUGHT for each. The derivation kept agreeing with the literal
# beside it while this file subtracted whatever it liked.
#
# The sweep that followed found the same six numbers recorded in SEVEN places
# at three precisions (c22c-copy-sweep.sh lists them). They now live in exactly
# one: c22c_source.json, read here, verified against live derivations by
# c22c_derive.py, and pinned in the fast suite by a DIGEST rather than a second
# copy.
#
# WHAT MOVED. The carried values are the derivations' own output, ceiling-
# rounded to 20 digits, instead of the record's 3-to-5-figure roundings. C22c
# rises by 3.0036931585923617932e-8 bit at n = 1e6 and 1.249454251229696301e-9
# at n = 8e6, both from COMPRESSION, which binds at both lengths. C22c is
# SUBTRACTED, so a larger C22c means a LOWER floor: the old values subtracted
# too little and the floor was permissive by exactly that amount. Nothing
# published changes materially -- 3.0e-8 against a C22c of 3.36e-3.
#
# AND THAT IS NOT THE REASON FOR THE FIX. The 3.0e-8 bound held only while the
# two copies happened to agree. An undetected drift in this file moved the
# floor by the size of the drift, in either direction, with the verification
# still green. The unbounded exposure is what closes.
#
# PARTLY CLOSED ALREADY, BY ACCIDENT: regression-constants.sh has pinned these
# six literals by value since OC-121, which was written for the mutation-
# landing hazard and not for this. It closed the fast-suite half of the defect
# without anyone intending to.
#
# REFUSAL, NOT A DEFAULT. If the source is absent, malformed, unstamped, or its
# derivation has changed since the value was stamped, this module raises at
# import and no floor is produced. There is no fallback table: a fallback would
# be a seventh copy, and it would be the one that runs on the day the source
# goes missing.
# =============================================================================
# The oracles' own directory, because this module is also loaded BY PATH --
# regression-constants.sh uses importlib.util.spec_from_file_location -- and in
# that case sys.path does not contain it. Without this the import below fails
# in the one caller whose whole job is to notice when these values move.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c22c_source as _c22c_src

C22C_FAMILIES_BY_N = _c22c_src.families_by_n()
C22C_BY_N = tuple((n0, max(f.values())) for n0, f in C22C_FAMILIES_BY_N)

def c22c_families(n):
    for n0, f in C22C_FAMILIES_BY_N:
        if n >= n0:
            return f, n0
    return None, None

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
    # F08 (OC-83): `if not w` tested TRUTHINESS, so every non-zero value passed.
    # bitsPerSymbol = 1.5 was accepted and used three times -- in h_orig / w, in
    # w * h', and in n = samples * w, which gave "n (bitstring length) 1500000
    # bits" for a width that cannot exist. The tool's own usage text says "Must
    # be between 1-8, inclusive", so that is the test: an integer in that range
    # and nothing else. A bool is rejected explicitly because True == 1 in
    # Python and `bitsPerSymbol: true` must not read as a 1-bit symbol.
    if isinstance(w, bool) or not isinstance(w, (int, float)) or float(w) != int(w) \
            or not (1 <= int(w) <= 8):
        raise SystemExit("REFUSED: %s records bitsPerSymbol=%r. The tool accepts an integer width "
                         "of 1-8 inclusive, so this is not a width any run of it produced, and a "
                         "per-bit figure derived from it would be arithmetic on a value that "
                         "cannot exist (F08)." % (report_path, w))
    w = int(w)
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
            # F08 (OC-83): THIS USED TO BE A NOTE, AND THE SCRIPT WENT ON TO
            # PRINT A FLOOR. The note's own words were "stop and resolve it
            # before using either", so the script told the reader to stop and
            # then did not stop itself. Demonstrated on a genuine report with
            # hOriginal 0.8 and hAssessed 0.1: the note was printed and two
            # floor figures followed it, exit 0.
            #
            # The two fields are different readings of the same measurement. If
            # they disagree, at least one is wrong, and which one is unknown --
            # so h' itself is unknown and nothing may be derived from it.
            raise SystemExit(
                "REFUSED: %s carries hAssessed %.17g where word_size * h' is %.17g. The C02 "
                "relation does not hold on this report, so one of the two readings is wrong and "
                "which one is not determinable from the report. h' is therefore unestablished "
                "and no figure is derived from it (F08)." % (report_path, ha, want))
        else:
            notes.append("consistency: hAssessed == word_size * h' to within 1e-12 relative, "
                         "as C02 describes.")
    samples = int(d.get('assessedSampleCount') or 0)
    n = samples * w
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

def report(hp, n, binder=None, cand=None, notes=(), src="", w=None, samples=None):
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
    # TWO DIFFERENT REQUIREMENTS, AND A BIT COUNT SATISFIES ONLY ONE (F08,
    # OC-83).
    #
    #   (a) SP 800-90B 3.1.1 item 1 requires at least 1,000,000 SAMPLES. That is
    #       a property of the dataset the standard will accept at all.
    #   (b) the C22c/ZALPHA term was MEASURED at bitstring lengths from
    #       1,000,000 BITS up, and this script will not extrapolate below that.
    #
    # Only (b) was checked, as `n < 1_000_000` on the BIT count. So 125,000
    # eight-bit samples -- one eighth of the standard's minimum -- gave
    # n = 1,000,000 bits and passed. Demonstrated on a report edited to exactly
    # that: "n (bitstring length) 1000000 bits", figures printed, exit 0.
    #
    # The sample minimum is checked FIRST because it decides whether there is a
    # compliant assessment to floor at all. A short run normally also carries
    # nonCompliantShortDataset, which this script already refuses -- this is the
    # same fact checked independently of that flag, because a figure must not
    # rest on a single field being set correctly.
    if samples is not None and samples < 1_000_000:
        raise SystemExit("REFUSED: %d samples is below the 1,000,000 SP 800-90B 3.1.1 item 1 "
                         "requires, so there is no compliant assessment to floor. Note that %d "
                         "samples at %d bits is %d bits, which satisfies the separate ZALPHA "
                         "length requirement -- a bit count is not a sample count (F08)."
                         % (samples, samples, w, n))
    if n < 1_000_000:
        raise SystemExit("REFUSED: n = %d is below the 1,000,000 bits the ZALPHA term was measured "
                         "at; this script will not extrapolate. Run OC-22's harness at this n." % n)
    bz, bz_n = c22c(n)
    a = C22A_PER_N * (n + 1)
    print()
    print("  term                                     value        why")
    print("  ---------------------------------------- ------------ " + "-" * 34)
    if w == 1:
        print("  C01/F10 MultiMMC chained lookup          %.3e    PROVED EXCLUSION: unreachable at width 1" % 0.0)
        print("    D_MMC=16, MAX_ENTRIES=100000; for binary data entries[d] <= 2^(d+2), so the cap")
        print("    cannot bind below d=15 and d=15 has no d+1 to suppress. A proof, not a measurement.")
    else:
        print("  C01/F10 MultiMMC chained lookup          %.3e    EVALUATED MARGIN, *not* a bound" % C01)
        print("    One measured overestimate from f10_over_8bit_1M. The mechanism is dictionary")
        print("    saturation, whose size is set by the data, so nothing here constrains it (A02).")
    print("  C22a P_local quantisation                %.3e    MEASURED, 8.08e-15 x (n+1), n = %d" % (a, n))
    print("    8.08e-15 = c * K, a PRODUCT OF TWO GRID MAXIMA. c = 0.4991's argmax is interior in")
    print("    every swept axis and bit-identical when the last arbitrary axis is extended nine")
    print("    orders (OC-63). K = 1.6189e-14 is attained at N = 5, r = 2 -- the FIRST r in the")
    print("    swept list -- and its interiority was never examined (F02, OC-78). The sweep's own")
    print("    worst realised inflation reaches 92.8% of this ceiling. MEASURED, not PROVED.")
    print("  C22b P_global' at N == 1                 %.3e    PROVED, conservative at every N" % C22B)
    fam, fam_n = c22c_families(n)
    print("  C22c ZALPHA vs the literal 2.576         %.3e    DERIVED, at n = %d" % (bz, bz_n))
    if fam:
        # SHAPE-07: emit the components, name the binding one, keep the margin.
        ranked = sorted(fam.items(), key=lambda kv: -kv[1])
        binding, bval = ranked[0]
        runner, rval = ranked[1]
        for name, val in ranked:
            print("      %-12s %.3e%s" % (name, val, "   <- BINDS" if name == binding else ""))
        print("      binding family: %s; margin to %s: %.3e bit (%.1fx)"
              % (binding, runner, bval - rval, bval / rval if rval else float('inf')))
    print("    COMPRESSION binds because com_exp is stationary at p = 1/64, so the sensitivity is")
    print("    quadratic on the approach to its cap and sigma_max carries a log2(num_blocks).")
    print("    Reproduced independently where checkable: num_blocks and dX' to three significant")
    print("    figures, and the collision family's whole ceiling to 0.07% (OC-62). Its fall with")
    print("    n is measured, not asserted: oracles/zalpha_ceiling_by_n.py.")
    print("    DERIVED THROUGHOUT as of OC-86, where it was DERIVED + MEASURED (F02, OC-78).")
    print("    dX' <= dz sigma_max / sqrt(v): Popoviciu bounds sigma_max, v = num_blocks - 1000 is")
    print("    exact. The ARGMAX is no longer searched for: com_exp is stationary at p = 2^-b by")
    print("    exact cancellation (d/dp com_exp = G'(p) - G'(q), and q = p there), p*|com_exp'(p)|")
    print("    was measured monotone away from the cap, so H is convex in X' and the widest rise")
    print("    of fixed width is the interval ENDING at the cap. The value is then one exact")
    print("    solve, not a maximum over a grid. oracles/compression_ceiling_exact.py, validated")
    print("    against SP 800-90B 6.3.4's own published worked example.")
    # A02: C01 is excluded at width 1 by proof, and is a MARGIN above it.
    c01 = 0.0 if w == 1 else C01
    c01_excluded = (w == 1)
    lit = hp - c01 - a - C22B - bz
    f07 = hp - c01 - a - C22B
    print()
    # THE LABEL, AND THE HISTORY OF THE LABEL, KEPT APART (OC-88).
    #
    # CURRENT, and the only thing this file asserts: the floor takes the
    # WEAKEST status among the terms it subtracts, and the printed label NAMES
    # the term holding it there. At width 1 that is
    #
    #     C01/F10  PROVED EXCLUSION    unreachable; a counting proof
    #     C22a     MEASURED            a product of two grid maxima (above)
    #     C22b     PROVED              zero, conservative at every N
    #     C22c     DERIVED             dX' from Popoviciu and an exact v; the
    #                                  ceiling an exact solve at a DERIVED
    #                                  argmax (OC-86)
    #
    # so the weakest is MEASURED and both readings are MEASURED FLOORS. Above
    # width 1, C01/F10 is an evaluated margin and neither reading is a floor at
    # all.
    #
    # SUPERSEDED, in order, and NOT re-asserted anywhere above -- this list is
    # the record of what this file used to say, not a statement of what holds:
    #
    #   A02/OC-55  "a certified floor is one where every subtracted term is a
    #              bound" -- the definition of a term retired at OC-78.
    #   OC-59      "C22c at ANY width is not reproduced by an independent
    #              derivation, which gives 7.49e-4 / 4.46e-4" -- WRONG. OC-62
    #              found the cause: that derivation computed the COLLISION
    #              family, and the tabulated term is COMPRESSION, 4.3-4.6x
    #              larger. OC-86 then computed the compression ceiling
    #              independently from SP 800-90B 6.3.4 and it agrees with
    #              production to six and seven significant figures.
    #   OC-59      "at width 1 the F07 reading is a certified floor and the
    #              literal reading is not" -- superseded twice over: by OC-62,
    #              which restored the literal reading, and by OC-78, which
    #              retired the label for both.
    #   OC-62      "the literal reading is a certified floor again" -- the
    #              correction was right about C22c and wrong about the label.
    #   OC-63      "C22a's constant is a supremum, so the term is a bound" --
    #              examined one of the two grid maxima the constant is a
    #              product of. F02/OC-78.
    #
    # WHY THE LIST AND NOT THE PROSE. These five statements stood here as flat
    # assertions, in sequence, above the current reasoning -- so this file
    # asserted FOUR TIMES that a reading is a certified floor while printing
    # MEASURED FLOOR, and restated OC-59's "not reproduced" after OC-86 had
    # settled it. That is exactly the shape OC-73 removed from this file once
    # before, reintroduced by the edit that retired the label. A live
    # instrument's comments must not contradict its behaviour; a dated record
    # of what they used to say is a different thing and belongs in a list that
    # cannot be mistaken for the present tense.
    # A CERTIFIED CLAIM RESTING ON AN UNCERTIFIED INPUT IS NOT CERTIFIED, and
    # that is now applied to this file's own label instead of being quoted in
    # it (F02, OC-78).
    #
    # "CERTIFIED FLOOR" IS RETIRED. It was printed whenever width == 1 and
    # C22a's supremacy was marked established, and the sentence that justified
    # it read: "every term is now a bound at width 1: C01/F10 excluded by
    # proof, C22a a MEASURED SUPREMUM, C22b zero, C22c a derived ceiling."
    # A measured supremum is not a proved bound. The list named its own
    # exception and then called the aggregate certified anyway.
    #
    # The label is now COMPOSITE: the floor takes the WEAKEST status among the
    # terms it actually subtracts, and the printed line NAMES the term holding
    # it there, so a reader learns what would have to change to strengthen it.
    #
    # At width 1 the statuses are:
    #   C01/F10   PROVED EXCLUSION   unreachable, a proof not a measurement
    #   C22a      MEASURED           a product of two grid maxima (above)
    #   C22b      PROVED             zero, conservative at every N
    #   C22c      DERIVED + MEASURED dX' derived, the ceiling a scan maximum
    # so the weakest is MEASURED and both readings are MEASURED FLOORS. The
    # F07 reading does not subtract C22c, but C22a alone already fixes the
    # weakest status, so the two readings share it -- which is why this is not
    # a per-reading distinction the way C01/F10 is.
    #
    # Nothing about the NUMBERS changed. A measured floor is still the most
    # defensible figure available and is still worth computing; what changed is
    # that it no longer claims a status its weakest input does not have.
    TERM_STATUS = {
        'C01/F10': 'PROVED EXCLUSION' if w == 1 else 'EVALUATED MARGIN',
        'C22a': 'MEASURED',
        'C22b': 'PROVED',
        'C22c': 'DERIVED + MEASURED',
    }
    # rank: the later in this tuple, the weaker
    RANK = ('PROVED', 'PROVED EXCLUSION', 'DERIVED', 'DERIVED + MEASURED',
            'MEASURED', 'EVALUATED MARGIN')

    def weakest(terms):
        """The weakest status among `terms`, and every term holding it there."""
        st = [(TERM_STATUS[t], t) for t in terms]
        worst = max(RANK.index(x[0]) for x in st)
        return RANK[worst], [t for sts, t in st if RANK.index(sts) == worst]

    # The LITERAL reading subtracts C22c; the F07 reading does not. C01/F10 is
    # subtracted only above width 1 -- at width 1 it is excluded by proof, so
    # it is listed either way and its status carries the difference.
    lit_status, lit_why = weakest(['C01/F10', 'C22a', 'C22b', 'C22c'])
    f07_status, f07_why = weakest(['C01/F10', 'C22a', 'C22b'])

    def label(status, why):
        if status == 'EVALUATED MARGIN':
            return "EVALUATED MARGIN (not a floor)"
        return "%s FLOOR (%s)" % (status, ", ".join(why))

    lab_lit = label(lit_status, lit_why)
    lab_f07 = label(f07_status, f07_why)
    print("  %-31s %.17g   (h' - %.6g)" % (lab_lit + ", literal", lit, hp - lit))
    print("  %-31s %.17g   (h' - %.6g)" % (lab_f07 + ", F07", f07, hp - f07))
    if not c01_excluded:
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
            # The SAMPLE count is passed separately from the bit length: the
            # two satisfy different requirements and only one of them was ever
            # checked (F08).
            report(hp, n, binder, cand, notes, w=w,
                   samples=int(d.get('assessedSampleCount') or 0),
                   src="%s  (%s, %s)" % (
                os.path.basename(path), d.get('type', '?'), d.get('toolVersion', '?')))
