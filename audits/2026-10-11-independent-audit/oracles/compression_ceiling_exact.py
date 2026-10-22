#!/usr/bin/env python3
"""C22c's COMPRESSION ceiling, computed independently of the production C++.

WHY THIS EXISTS (F-item 1 of 2026-10-21, OC-86).

`C22c` is the term `entropy_floor.py` subtracts, and the COMPRESSION family is
the one that binds. `zalpha_ceiling_by_n.py` reproduces its `dX'` and its
`num_blocks` -- but printed, for the ceiling itself:

    | compression ceiling | 1000000 | 3.360e-03 | (production solve, not reimplemented here) | n/a |

So the value actually subtracted from a reported min-entropy figure had NEVER
been computed by anything but the production solve. `OC-62` said the record was
"reproduced where it can be checked independently", which was true and narrower
than the conclusion drawn from it: what was checked was the INPUT to the
ceiling, not the ceiling.

Rather than scan through production's own `comp` entry point, this computes
`G(z)` FROM SP 800-90B 6.3.4 STEP 7 AS WRITTEN:

    G(z) = (1/v) * sum_{t=d+1}^{N} sum_{u=1}^{t} log2(u) F(z,t,u)

    F(z,t,u) = z^2 (1-z)^(u-1)   if u < t
             = z   (1-z)^(t-1)   if u = t

    X' = G(p) + (2^b - 1) G(q),   q = (1-p)/(2^b - 1),   b = 6
    min-entropy = -log2(p)/b

and is VALIDATED AGAINST THE STANDARD'S OWN WORKED EXAMPLE, not against the
tool: 6.3.4's example has d = 4, L = 48, N = 8, v = 4, X' = 1.4617, and NIST
publishes p = 0.5715 with min-entropy 0.1345. That is an external check of this
file, which is the whole point -- `OC-41` is the record of a harness that
re-implemented a production function, disagreed with it, and had no third party
to adjudicate. The worked example is that third party.

THE DOUBLE SUM IS REORDERED, EXACTLY ONCE, AND THE REORDERING IS THE ONLY
CLEVERNESS HERE. Swapping the order of summation:

    sum_{t=d+1}^{N} sum_{u=1}^{t-1} log2(u) z^2 (1-z)^(u-1)
      = z^2 sum_{u=1}^{N-1} log2(u) (1-z)^(u-1) * #{t : d+1 <= t <= N, t > u}

and that count is (N-d) for u <= d and (N-u) for u > d. So

    G(z) = (1/v) [ z^2 ( (N-d) * sum_{u=1}^{d} log2(u)(1-z)^(u-1)
                         + sum_{u=d+1}^{N-1} (N-u) log2(u)(1-z)^(u-1) )
                   + z * sum_{t=d+1}^{N} log2(t)(1-z)^(t-1) ]

one pass, no inner loop. (Production arrives at the same shape by a different
route; this derivation is from the formula above, not from that code.)

TRUNCATION IS BOUNDED, NOT GUESSED. (1-z)^(u-1) decays geometrically, and at
z ~ 1/64 it is below 1e-45 by u ~ 6600. The remaining terms carry a factor at
most N * log2(N), so a tail bound of that times the next power is added and
printed; the sum stops when the bound is below 10^-(dps-5).
"""
import sys
from mpmath import mp, mpf, log, sqrt, mpmathify

mp.dps = 50
LN2 = log(2)


def log2(x):
    return log(x) / LN2


def G(z, d, N, v, tail_eps=None):
    """SP 800-90B 6.3.4 step 7's G, reordered as derived in the docstring."""
    z = mpf(z)
    one_minus = 1 - z
    if not (0 < z < 1):
        raise ValueError("z must lie in (0,1); got %s" % z)
    if tail_eps is None:
        tail_eps = mpf(10) ** (-(mp.dps - 5))

    s_dict = mpf(0)      # sum_{u=1}^{d} log2(u)(1-z)^(u-1)
    s_test = mpf(0)      # sum_{u=d+1}^{N-1} (N-u) log2(u)(1-z)^(u-1)
    s_tie = mpf(0)       # sum_{t=d+1}^{N} log2(t)(1-z)^(t-1)
    pw = mpf(1)          # (1-z)^(u-1)
    truncated_at = None
    for u in range(1, N + 1):
        l2 = log2(u) if u > 1 else mpf(0)
        if u <= d:
            s_dict += l2 * pw
        elif u <= N - 1:
            s_test += (N - u) * l2 * pw
        if u >= d + 1:
            s_tie += l2 * pw
        # Stop when even the largest possible remaining factor cannot matter.
        if u > d and pw * N * (log2(N) if N > 1 else 1) < tail_eps:
            truncated_at = u
            break
        pw *= one_minus

    g = (z * z * ((N - d) * s_dict + s_test) + z * s_tie) / v
    return g, truncated_at


def com_exp(p, d, N, v, b=6):
    """X' = G(p) + (2^b - 1) G(q), q = (1-p)/(2^b - 1)."""
    k = 2 ** b
    p = mpf(p)
    q = (1 - p) / (k - 1)
    gp, _ = G(p, d, N, v)
    gq, _ = G(q, d, N, v)
    return gp + (k - 1) * gq


def solve_p(target, d, N, v, b=6, lo=None, hi=None):
    """Binary search for p in [2^-b, 1) with com_exp(p) = target.

    com_exp is DECREASING in p above 2^-b (more probable most-likely symbol =>
    shorter distances => smaller Maurer statistic), so the bracket is inverted
    relative to the usual convention. 6.3.4 names the bounds 2^-b and 1.
    """
    k = 2 ** b
    lo = mpf(1) / k if lo is None else mpf(lo)
    hi = mpf(1) - mpf(10) ** -30 if hi is None else mpf(hi)
    f_lo = com_exp(lo, d, N, v, b) - target
    f_hi = com_exp(hi, d, N, v, b) - target
    if f_lo * f_hi > 0:
        return None, (float(f_lo), float(f_hi))
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = com_exp(mid, d, N, v, b) - target
        if f_mid == 0:
            return mid, None
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi, f_hi = mid, f_mid
        if hi - lo < mpf(10) ** -(mp.dps - 10):
            break
    return (lo + hi) / 2, None


Z_TOOL = mpf("2.5758293035489008")      # the exact 0.995 quantile the tool uses
Z_SPEC = mpf("2.576")                   # the value 6.3.4 step 6 prints
COMPRESSION_D = 1000
B = 6


def ceiling_at(n, verbose=True):
    """The C22c COMPRESSION ceiling at bitstring length n, independently.

    The ceiling is the largest entropy change a dX' shift in X' can cause. The
    argmax is NOT searched for: it is DERIVED. H(X') = -log2(p(X'))/b with
    com_exp decreasing in p, so H increases with X'; and com_exp is STATIONARY
    at p = 2^-b, which is proved rather than observed --

        d/dp com_exp = G'(p) - G'(q)   (since dq/dp = -1/(2^b - 1)),

    and at p = 2^-b, q = (1 - 2^-b)/(2^b - 1) = 2^-b, so the two terms cancel
    exactly. So dH/dX' diverges at the cap, H is convex there, and the dX'-wide
    interval with the largest rise is the one ENDING at the cap. Production's
    801-point scan finds its argmax at `cap - 1.0 dX'`, which is that interval;
    here it is the starting point rather than a result.
    """
    N = n // B
    d = COMPRESSION_D
    v = N - d
    if v < 2:
        raise ValueError("n = %d leaves v = %d test blocks" % (n, v))
    cap_g, trunc = G(mpf(1) / 2 ** B, d, N, v)
    cap = (2 ** B) * cap_g                     # com_exp(2^-b), both G terms equal
    sigma_max = mpf("0.5907") * log2(N) / 2    # Popoviciu, values in [0, log2 N]
    dxp = (Z_SPEC - Z_TOOL) * sigma_max / sqrt(v)
    target = cap - dxp
    # p* is just above 2^-b; bracket generously but not to 1, so the bisection
    # spends its iterations where the root is.
    p_star, why = solve_p(target, d, N, v, b=B, lo=mpf(1) / 2 ** B, hi=mpf("0.05"))
    if p_star is None:
        raise RuntimeError("no bracket for n=%d: %s" % (n, why))
    ceiling = log2((2 ** B) * p_star) / B      # H(cap) - H(p*), since H(cap) = 1
    if verbose:
        print("n = %d:  N = %d  v = %d  (G truncated at u = %s)" % (n, N, v, trunc))
        print("  cap  com_exp(2^-6)    = %s" % mp.nstr(cap, 17))
        print("  sigma_max            = %s" % mp.nstr(sigma_max, 6))
        print("  dX'                  = %s" % mp.nstr(dxp, 6))
        print("  p* with com_exp = cap - dX'  = %s" % mp.nstr(p_star, 12))
        print("  p* - 2^-6            = %s" % mp.nstr(p_star - mpf(1) / 64, 6))
        print("  CEILING (bit)        = %s" % mp.nstr(ceiling, 8))
    return dict(n=n, N=N, v=v, cap=cap, sigma_max=sigma_max, dxp=dxp,
                p_star=p_star, ceiling=ceiling)


if __name__ == '__main__':
    # The standard's own worked example, first, as a self-check on this file.
    p, _ = solve_p(mpf("1.4617"), 4, 8, 4)
    ok = abs(p - mpf("0.5715")) < mpf("0.00005")
    print("SELF-CHECK against SP 800-90B 6.3.4's worked example (d=4, N=8, v=4, X'=1.4617):")
    print("  NIST publishes p = 0.5715, min-entropy 0.1345")
    print("  this file: p = %s, min-entropy %s  ->  %s"
          % (mp.nstr(p, 8), mp.nstr(-log2(p) / 6, 6), "AGREES" if ok else "*** DISAGREES ***"))
    if not ok:
        raise SystemExit("the implementation does not reproduce the standard's example; "
                         "nothing below it means anything")
    print()
    # THE RECORDED VALUES ARE KEPT AS STRINGS, because their PRECISION is part
    # of the datum and an mpf does not carry it. The first draft of this block
    # counted significant figures by rendering mpf("3.36e-3") to 20 places,
    # got 6 figures out of the binary noise, derived a tolerance of 5e-9, and
    # declared both rows DISAGREE -- the same mistake F02 fixed in
    # zalpha_ceiling_by_n.py by switching to repr(). A string cannot have that
    # problem.
    #
    # TWO comparisons, because they are two different claims:
    #   TABULATED  the 3-figure values entropy_floor.py carries and subtracts.
    #   SCAN       what production's own 801-point scan printed, to 5 figures
    #              (p_local_exact.py). Agreement here is the stronger result:
    #              it compares this derivation against that computation at the
    #              precision the computation reported, not at the precision the
    #              table rounded to.
    TABULATED = {10 ** 6: "3.36e-3", 8 * 10 ** 6: "2.16e-3"}
    SCAN = {10 ** 6: "3.3599e-3", 8 * 10 ** 6: "2.1644e-3"}

    def sig_and_tol(text):
        """Significant figures and half-unit-in-the-last-digit, from the TEXT."""
        import math
        mant = text.split('e')[0].split('E')[0].replace('.', '').replace('-', '')
        mant = mant.lstrip('0')
        sf = max(1, len(mant.rstrip('0')) if mant.rstrip('0') else 1)
        val = mpf(text)
        e = math.floor(math.log10(abs(float(val))))
        return sf, mpf("0.5") * mpf(10) ** (e - (sf - 1)), val

    bad = 0
    rows = []
    for n in sorted(TABULATED):
        r = ceiling_at(n)
        for label, table in (("tabulated", TABULATED), ("production scan", SCAN)):
            sf, tol, val = sig_and_tol(table[n])
            diff = r['ceiling'] - val
            agree = abs(diff) <= tol
            if not agree:
                bad += 1
            rows.append((n, label, table[n], sf, r['ceiling'], diff, tol, agree))
            print("  vs %-16s %s  (%d sig figs)" % (label, table[n], sf))
            print("     residual  = %s   (%.4f %% of it)"
                  % (mp.nstr(diff, 6), float(100 * diff / val)))
            print("     tolerance = %s   (half a unit in the last digit)" % mp.nstr(tol, 6))
            print("     used      = %.1f %% of the tolerance" % float(100 * abs(diff) / tol))
            print("     VERDICT   = %s" % ("AGREES" if agree else "*** DISAGREES ***"))
        print()
    print("| n | compared with | value | sig figs | independent | residual | tolerance | agrees |")
    print("|---:|---|---:|---:|---:|---:|---:|---|")
    for n, label, text, sf, mine, diff, tol, agree in rows:
        print("| %d | %s | %s | %d | %s | %s | %s | %s |"
              % (n, label, text, sf, mp.nstr(mine, 8), mp.nstr(diff, 3),
                 mp.nstr(tol, 3), "yes" if agree else "**NO**"))
    raise SystemExit(1 if bad else 0)
