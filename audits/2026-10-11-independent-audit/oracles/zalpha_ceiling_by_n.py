#!/usr/bin/env python3
"""C22c: is the ZALPHA ceiling MONOTONE DECREASING in n?

WHY THIS EXISTS. entropy_floor.py subtracts the C22c term measured "at the
largest measured n not exceeding the actual n", and justifies that as an upper
bound by asserting the ceiling falls with n. That is the premise the rule rests
on, and it was an analytic sketch (dX' ~ sigma_max/sqrt(v)) rather than a
measurement. An observed maximum is not a bound, and neither is an asserted
monotonicity.

WHAT IS MEASURED. For the upper confidence bound the tool forms,

    ub(p, n, z) = min(1, p + z*sqrt(p(1-p)/(n-1))),    H = -log2(ub)

the C22c term is max over estimators of H(z_tool) - H(2.576), where
z_tool = 2.5758293035489008 is the exact 0.995 normal quantile and 2.576 is the
standard's printed rounding. This maximises that difference over p for each n,
so each row is the worst case at that length rather than one instance.

TWO CONTROLS, because a measurement that cannot fail proves nothing:
  * SELF-COMPARISON -- every value is computed at two working precisions and
    must agree, so the answer is not a precision artefact.
  * LIVE SENSITIVITY -- dz is perturbed and the ceiling must move, so the
    computation is demonstrably not blind to its own input.

Usage:  zalpha_ceiling_by_n.py
"""
from mpmath import mp, mpf, log, sqrt

# THE QUANTILES ARE BUILT AT A FIXED HIGH PRECISION, AND THAT IS A REPAIR
# (OC-125). These two were plain module-level mpf() calls, so each was built at
# whatever mp.dps happened to be in effect WHEN THIS MODULE WAS IMPORTED -- the
# mpmath default of 53 bits when run as a script, 50 digits when something else
# had already set it. z_spec - z_tool = 1.706964511e-4 out of two numbers near
# 2.576, so at 53 bits the difference loses twelve of its sixteen digits to
# cancellation, and every ceiling computed from it inherits that. The `dps`
# argument these functions take could not fix it: it sets the WORKING
# precision, and the constants were already rounded.
#
# Measured: the collision ceiling at n = 8e6 comes out 0.00046643872746941443
# with the constants built at 53 bits and 0.00046643872746936080 with them
# built at 50 digits or more. Same code, same dps argument, different import
# order.
#
# NEITHER OF THIS FILE'S TWO CONTROLS COULD SEE IT. The self-comparison
# recomputes every row at a second working precision, which does not touch the
# constants; the live-sensitivity control perturbs z_spec by 1e-5, which is
# eight orders of magnitude larger than the error. And every comparison this
# file made was at three significant figures, where the error is invisible.
# What exposed it was the EXACT comparison against the carried value that
# OC-125 introduced -- the first check here that read more than three digits.
#
# 120 digits because the decimal strings have at most 17: an mpf built at 120
# digits represents them exactly, so no working precision up to 120 can be
# limited by them.
_Q_DPS = mp.dps
mp.dps = 120
Z_TOOL = mpf("2.5758293035489008")
Z_SPEC = mpf("2.576")
mp.dps = _Q_DPS
# SP 800-90B 6.3.4 step 2: the first d blocks are the dictionary, the remaining
# v = num_blocks - d are the test blocks the statistic averages over.
# cpp/non_iid/compression_test.h: `d = 1000;`.
COMPRESSION_D = 1000

def ub(p, n, z):
    v = p + z * sqrt(p * (1 - p) / (n - 1))
    return v if v < 1 else mpf(1)

def gap(p, n, ztool, zspec):
    ln2 = log(2)
    return (-log(ub(p, n, ztool)) / ln2) - (-log(ub(p, n, zspec)) / ln2)

def worst_proportion(n, dps, ztool=Z_TOOL, zspec=Z_SPEC):
    """max over p of the entropy gap for a PROPORTION estimator at this n.

    THE DOMAIN IS p >= 1/n, NOT p > 0. The first version of this swept down to
    1e-6 and then refined to p0/4, and reported its maximum at p = 2.5e-07 --
    BELOW 1/n, i.e. a proportion no count can produce. The gap grows without
    limit as p -> 0, so an unconstrained sweep reports the edge of its own grid
    and calls it a worst case. p-hat is mode/n with mode >= 1.
    """
    mp.dps = dps
    pmin = mpf(1) / n
    best = (mpf(0), pmin)
    cand = [pmin, pmin * 2, pmin * 10, mpf("0.004"), mpf("0.5"), mpf(1) - pmin]
    cand += [pmin * (mpf(10) ** mpf(k / mpf(4))) for k in range(0, 25)]
    for p in cand:
        if not (pmin <= p < 1):
            continue
        g = gap(p, n, ztool, zspec)
        if g > best[0]:
            best = (g, p)
    return best

LN2 = log(2)

def h_col(xp):
    """SP 800-90B 6.3.2: p from X', H = -log2(p), clamped at X' >= 2.5."""
    xp = xp if xp > 2 else mpf(2)
    if xp >= mpf("2.5"):
        return mpf(1)
    return -log(mpf("0.5") + sqrt(mpf("1.25") - mpf("0.5") * xp)) / LN2

def worst_collision(n, dps, ztool=Z_TOOL, zspec=Z_SPEC):
    """COLLISION ceiling at this bitstring length n (SP 800-90B 6.3.2).

    X' = X-bar - z*s/sqrt(v); p = 1/2 + sqrt(1.25 - X'/2); H capped at 1 when
    X' >= 2.5. dH/dX' diverges at the cap but the INFLATION does not, because H
    is capped, so the ceiling is the quadratic form

        max dH = (2/ln2) * sqrt(dX'/2),   dX' <= dz * (1/2) / sqrt(v)

    with s <= 1/2 (t in {2,3}) and v >= n/3. BOUND v THE WAY THE RECORD DOES:
    the first version of this used v = n/2.5, which is not a bound but a
    typical value, and it produced a ceiling 4.6% below the recorded one. A
    bound computed from a typical value is not a bound (OC-62).
    """
    mp.dps = dps
    v = mpf(n) / 3
    dx = (zspec - ztool) * mpf("0.5") / sqrt(v)
    return (2 / log(2)) * sqrt(dx / 2), dx

def worst_compression_dx(n, dps, ztool=Z_TOOL, zspec=Z_SPEC):
    """COMPRESSION's dX' bound (SP 800-90B 6.3.4) -- THE FAMILY THAT BINDS.

    com_exp(p) = G(p) + 63*G((1-p)/63) is STATIONARY at p = 1/64, so the
    sensitivity is quadratic on the approach to the cap exactly as for
    collision, and a linearised bound would be wrong.

        dX' <= dz * sigma_max / sqrt(v),
        sigma_max = 0.5907 * log2(num_blocks) / 2   (Popoviciu),
        num_blocks = n // 6,  v = num_blocks - d,  d = 1000

    v IS num_blocks MINUS d, AND THIS SCRIPT HAD v = num_blocks (F02).
    SP 800-90B 6.3.4 sets d = 1000 dictionary blocks and averages over the
    remaining v = num_blocks - d TEST blocks, which is what production does
    (cpp/non_iid/compression_test.h: `d = 1000; num_blocks = len/b; ...
    v = num_blocks - d`). PRODUCTION IS RIGHT. So is the record: the tabulated
    C22c values came from p_local_exact.py, which has `v_ = nb_ - 1000`. This
    HELPER -- the thing whose whole job is to reproduce the record
    independently -- was the only one of the three that was wrong.

    The direction matters. Too large a v makes dX' too SMALL, which makes the
    subtracted term too small and the floor too HIGH: the unsafe direction.
    Measured: 2.1422e-06 against the correct 2.1486e-06 at n = 1e6, 0.300% low,
    and 0.038% low at n = 8e6.

    AND THE COMPARATOR BELOW AGREED ANYWAY, because its tolerance was a flat
    1% while the record states these to three significant figures. 0.300% is
    inside 1% and outside the third significant figure -- the helper's value
    rounds to 2.14e-06 where the record says 2.15e-06. A comparator whose
    resolution is coarser than the precision it is checking reports agreement
    it has not established, so the tolerance is now DERIVED from the number of
    significant figures in the recorded value.

    num_blocks is also an integer COUNT, floor-divided in production; this used
    mpf(n)/6 and returned 166666.667 against the recorded 166666.

    This returns dX' only. The final ceiling in the record comes from SCANNING
    X' down from the cap G(1/64) through the PRODUCTION compression solve, and
    this script deliberately does not reimplement that solve: a harness that
    re-implemented production functions instead of calling them, and disagreed
    with the tool, is OC-41. dX' is what can be checked independently, and it
    is checked below.
    """
    mp.dps = dps
    nb = n // 6                    # an integer count of blocks, as production floor-divides
    v = nb - COMPRESSION_D         # the TEST blocks, not all of them
    if v < 2:
        raise ValueError("n = %d leaves v = %d test blocks; 6.3.4's 1/(v-1) needs v >= 2" % (n, v))
    sigma_max = mpf("0.5907") * (log(nb) / log(2)) / 2
    return (zspec - ztool) * sigma_max / sqrt(v), nb, sigma_max

def sigfigs(x):
    """How many significant figures the RECORDED value is written to.

    A recorded 3.36e-03 claims three; 166666 claims six. The mantissa's digits
    with trailing zeros stripped is the honest count -- a trailing zero in a
    recorded figure is ambiguous, and treating it as insignificant makes the
    tolerance wider, never narrower, so the ambiguity cannot make this check
    pass something it should fail.
    """
    # repr() of a float is the SHORTEST decimal that round-trips, which is the
    # literal the record was written with. "%.17e" is not: it prints
    # 2.14999999999999996e-06 for a recorded 2.15e-06, so counting its digits
    # gave 18 significant figures and a tolerance of zero -- a check that can
    # never pass is as useless as one that can never fail.
    m = repr(abs(float(x))).split("e")[0].replace(".", "").lstrip("0").rstrip("0")
    return max(1, len(m))


def agrees(recorded, here):
    """Agreement AT THE PRECISION THE RECORD CLAIMS (F02).

    The tolerance was a flat 1% on values recorded to three significant
    figures. 1% is four times wider than the third figure, so a 0.300% error in
    this script's own compression v -- which changed the recorded 2.15e-06 to
    2.14e-06 -- was reported as agreement. A comparator with coarser resolution
    than the figure it checks cannot establish agreement; it can only fail to
    find disagreement.

    Half a unit in the last significant place is exactly the width within which
    two numbers round to the same recorded figure, so that is the tolerance.
    """
    import math
    recorded = float(recorded)
    if recorded == 0:
        return (float(here) == 0, 0.0)
    # HALF A UNIT IN THE LAST RECORDED DIGIT, ABSOLUTELY. Expressing it as a
    # relative tolerance invites the mistake made in the first draft of this
    # function: 0.5 * 10^-(sf-1) is half a unit in the LEADING digit, 0.5% for
    # three figures, which is twice too wide at a mantissa of 2.15 and was the
    # same shape of error as the 1% it replaced.
    e = math.floor(math.log10(abs(recorded)))
    tol_abs = 0.5 * 10.0 ** (e - (sigfigs(recorded) - 1))
    return (abs(recorded - float(here)) <= tol_abs, tol_abs / abs(recorded))


def main():
    NS = [1_000_000, 2_000_000, 4_000_000, 8_000_000, 16_000_000, 64_000_000]
    print("C22c: the ZALPHA gap (exact 0.995 quantile vs the printed 2.576), by length.")
    print("z_tool = %s   z_spec = %s   dz = %.10e" % (Z_TOOL, Z_SPEC, float(Z_SPEC - Z_TOOL)))
    print()
    print("A. PROPORTION estimators (MCV, t-Tuple, LRS, the P_global' terms), p >= 1/n")
    print("| n | worst gap (bit) | at p | dps 80 agrees | vs previous |")
    print("|---:|---:|---:|---|---|")
    prev, ok_mono_a, ok_self = None, True, True
    for n in NS:
        g, pp = worst_proportion(n, 50)
        g2, _ = worst_proportion(n, 80)
        agree = abs(g - g2) < mpf("1e-20")
        ok_self = ok_self and agree
        # The proportion family's gap is the CLOSED FORM dz/((1+z)ln2), which is
        # independent of n, so it is LEVEL rather than falling. A strict `>`
        # comparison on a theoretically constant quantity reports spurious
        # non-monotonicity from which candidate p happens to hit the maximum, and
        # the first version of this printed "*** RISES ***" for exactly that.
        # Compare with a tolerance, and call level what is level.
        if prev is None:
            mono = "-"
        elif g <= prev or abs(g - prev) < mpf("1e-12"):
            mono = "falls" if g < prev - mpf("1e-12") else "level (closed form, n-independent)"
        else:
            mono = "*** RISES ***"
            ok_mono_a = False
        print("| %d | %.6e | %.6g | %s | %s |" % (n, float(g), float(pp), "yes" if agree else "NO", mono))
        prev = g
    closed = (Z_SPEC - Z_TOOL) / ((1 + Z_TOOL) * LN2)
    print()
    print("  closed form at p = 1/n:  dz/((1+z)ln2) = %.6e bit, independent of n" % float(closed))
    print()
    print("B. COLLISION estimator (v >= n/3, s <= 1/2, as the record bounds them)")
    print("| n | dX' | ceiling (bit) | dps 80 agrees | vs previous |")
    print("|---:|---:|---:|---|---|")
    prev, ok_mono_b = None, True
    coll = {}
    for n in NS:
        g, dx = worst_collision(n, 50)
        g2, _ = worst_collision(n, 80)
        agree = abs(g - g2) < mpf("1e-20")
        ok_self = ok_self and agree
        mono = "-" if prev is None else ("falls" if g <= prev else "*** RISES ***")
        if prev is not None and g > prev: ok_mono_b = False
        coll[n] = g
        print("| %d | %.4e | %.6e | %s | %s |" % (n, float(dx), float(g), "yes" if agree else "NO", mono))
        prev = g
    print()
    print("C. COMPRESSION estimator -- THE ONE THAT BINDS (num_blocks = n/6)")
    print("| n | num_blocks | sigma_max | dX' | vs previous |")
    print("|---:|---:|---:|---:|---|")
    prev, ok_mono_c = None, True
    comp_dx = {}
    for n in NS:
        dx, nb, sm = worst_compression_dx(n, 50)
        mono = "-" if prev is None else ("falls" if dx <= prev else "*** RISES ***")
        if prev is not None and dx > prev: ok_mono_c = False
        comp_dx[n] = dx
        print("| %d | %d | %.4f | %.4e | %s |" % (n, int(nb), float(sm), float(dx), mono))
        prev = dx
    print()
    # LIVE SENSITIVITY
    gb, _ = worst_collision(8_000_000, 50)
    gp, _ = worst_collision(8_000_000, 50, zspec=Z_SPEC + mpf("1e-5"))
    live = gp != gb
    print("live sensitivity: perturbing z_spec by 1e-5 moves the collision ceiling")
    print("                  %.6e -> %.6e  ->  %s" % (float(gb), float(gp), "LIVE" if live else "*** BLIND ***"))
    print("self-comparison : every row recomputed at dps 80 -> %s" % ("agrees" if ok_self else "*** DISAGREES ***"))
    print("monotonicity    : proportion %s; collision %s; compression dX' %s"
          % ("level (closed form)" if ok_mono_a else "FAILS",
             "holds" if ok_mono_b else "FAILS", "holds" if ok_mono_c else "FAILS"))
    print()
    print("D. AGAINST THE RECORD (ORCHESTRATOR-CHECKS.md, OC-22 Part 3)")
    # THE CEILING VALUES COME FROM THE ONE SOURCE (OC-125). This block used to
    # carry its own copies --
    #
    #     REC_COLL = {1_000_000: (1.48e-7, 7.84e-4), 8_000_000: (5.23e-8, 4.66e-4)}
    #     REC_COMP = {1_000_000: (166666, 2.15e-6, 3.36e-3), ...}
    #
    # the second of which held the compression ceiling as well, so the six
    # family values were recorded in SEVEN places and nothing compared the copy
    # that was subtracted against the copy a derivation verified. The three
    # ceilings now come from c22c_source.json; the collision dX' and the
    # compression num_blocks and dX' stay here, because they are INPUTS to the
    # ceilings rather than the ceilings, and the one-source rule is scoped to
    # the six values C22c maxes over. c22c-copy-sweep.sh states and enforces
    # that scope.
    #
    # The collision family is also compared EXACTLY against the carried value
    # here -- not only against the record's three figures -- because this is
    # the derivation that produced it.
    import c22c_source as SRC
    from decimal import Decimal
    try:
        _doc = SRC.validate()
    except SRC.C22cSourceError as exc:
        print("   *** the C22c one source does not validate: %s" % exc)
        return 1
    _digits = _doc['digits']
    _by_n = {row['n']: row for row in _doc['rows']}
    REC_COLL = {n: (dx, float(_by_n[n]['collision']['record_3fig']))
                for n, dx in ((1_000_000, 1.48e-7), (8_000_000, 5.23e-8))}
    REC_COMP = {n: (nb, dx, float(_by_n[n]['compression']['record_3fig']))
                for n, nb, dx in ((1_000_000, 166666, 2.15e-6),
                                  (8_000_000, 1333333, 8.89e-7))}
    ok_rec = True
    print("| quantity | n | recorded | here | agrees |")
    print("|---|---:|---:|---:|---|")
    for n, (rdx, rc) in sorted(REC_COLL.items()):
        g, dx = worst_collision(n, 50)
        for lab, rv, mv in (("collision dX'", rdx, float(dx)), ("collision ceiling", rc, float(g))):
            ok, tol = agrees(rv, mv)
            ok_rec = ok_rec and ok
            print("| %s | %d | %.3e | %.3e | %s (tol %.3f%%) |"
                  % (lab, n, rv, mv, "yes" if ok else "*** NO ***", 100 * tol))
    for n, (rnb, rdx, rc) in sorted(REC_COMP.items()):
        dx, nb, sm = worst_compression_dx(n, 50)
        for lab, rv, mv in (("compression num_blocks", rnb, float(nb)), ("compression dX'", rdx, float(dx))):
            ok, tol = agrees(rv, mv)
            ok_rec = ok_rec and ok
            print("| %s | %d | %.6g | %.6g | %s (tol %.3f%%) |"
                  % (lab, n, rv, mv, "yes" if ok else "*** NO ***", 100 * tol))
        print("| compression ceiling | %d | %.3e | (derived in compression_ceiling_exact.py, compared there) | n/a |" % (n, rc))
    print()
    print("E. AGAINST THE CARRIED VALUE -- the collision number that is SUBTRACTED")
    print("| n | carried | this derivation, rounded up to %d digits | exact |" % _digits)
    print("|---:|---:|---:|---|")
    ok_carried = True
    for n in sorted(REC_COLL):
        g, _dx = worst_collision(n, 50)
        want = SRC.round_up(mp.nstr(g, _digits + 20, strip_zeros=False), _digits)
        got = Decimal(_by_n[n]['collision']['value'])
        ok = (want == got)
        ok_carried = ok_carried and ok
        print("| %d | %s | %s | %s |" % (n, got, want,
              "yes" if ok else "*** NOT THIS DERIVATION'S OUTPUT ***"))
    print()
    if not ok_carried:
        print("   the carried collision value is not what this file computes; the")
        print("   value entropy_floor.py subtracts does not come from a live")
        print("   derivation. Re-run c22c_derive.py --restamp.")
    print()
    if ok_rec:
        print("=> THE RECORD'S C22c IS REPRODUCED where it can be checked independently.")
        print("   The TABULATED term is the COMPRESSION ceiling, and the maximum over")
        print("   estimators is what entropy_floor.py subtracts. Its dX' and num_blocks")
        print("   reproduce to three significant figures; its final ceiling is derived")
        print("   from 6.3.4 step 7 by compression_ceiling_exact.py, which this script")
        print("   deliberately does not duplicate (OC-41, OC-86).")
        print()
        print("   OC-59 SAID THE TABULATED VALUES DID NOT REPRODUCE. That was wrong: it")
        print("   computed the COLLISION family, which is 4.3-4.6x smaller, and the ratio")
        print("   it reported as unexplained was simply compression/collision. The term")
        print("   is a derived ceiling, so it IS a bound, and nothing is being thrown")
        print("   away by subtracting it (OC-62).")
    else:
        print("=> some recorded quantity is NOT reproduced; read the table above.")
    return 0 if (ok_mono_b and ok_mono_c and ok_self and live and ok_rec
                 and ok_carried) else 1

    return 0 if (ok_mono_a and ok_mono_b and ok_self and live) else 1

if __name__ == "__main__":
    raise SystemExit(main())
