#!/usr/bin/env python3
"""The restart sanity-check cutoff, from first principles, with the integer
quantile CERTIFIED rather than read off a float.

WHY THIS EXISTS. An outside audit computed 684 at H_I = 0.696 where this
project had REPORTED 683. The production C++ and oracles/restart_cutoff_exact.py
both say 684, so the 683 was a reporting error -- but "two of my own tools
agree" is not an argument, because they share a design. This script derives the
number from the definition, in exact rational arithmetic, and certifies the
integer boundary by showing the tail straddles alpha with margins far larger
than the arithmetic error.

THE CONVENTION, WRITTEN DOWN, because the two candidate answers differ by one
and a convention also differs by one:

  * n = 1000 trials per row or column (a 1000x1000 restart matrix).
  * alpha is the PER-TEST level. SP 800-90B 3.1.4.3 step 1 sets 0.000005;
    1 - (1 - 5e-6)^2000 = 0.00995, i.e. the Sidak correction for 2000 tests at
    a 1 % family-wise rate, which is where that number comes from.
  * The cutoff is the SMALLEST m with P(X_max <= m) >= 1 - alpha.
  * COUNTS AT THE CUTOFF ARE ACCEPTED. The test fails iff X_max > cutoff
    (restart_main.cpp:795). This matches the audit's stated convention.
  * At width 1, p = 2^-H_I lies in (0.5, 1), so floor(1/p) = 1 and the
    worst-case configuration is exactly two cells, p and 1-p. Then
    max(X, n-X) <= m iff n-m <= X <= m, so
        P(X_max <= m) = sum_{j=n-m}^{m} C(n,j) p^j (1-p)^(n-j)
    and the tail is the two-sided sum. The PRINTED 3.1.4.3 formula uses the
    MAJORITY cell's one-sided tail only, which is why it can be one lower.

Usage:  restart_cutoff_certified.py H_I [H_I ...]
"""
import sys
from decimal import Decimal, getcontext
from math import comb

N = 1000
ALPHA_SPEC  = Decimal("0.000005")                       # 3.1.4.3 step 1, as printed
# Sidak for 2000 tests at a 1% family-wise rate: 1 - 0.99^(1/2000)
def sidak_alpha(prec):
    getcontext().prec = prec
    return Decimal(1) - (Decimal("0.99") ** (Decimal(1) / Decimal(2000)))

def tails(h, m, prec, p=None):
    """(two_sided_tail, majority_only_tail) at precision `prec`.

    Each tail is seeded with ONE exact binomial term and then walked outward by
    the ratio term_{j+1}/term_j = (n-j)/(j+1) * p/q, stopping when the terms
    stop mattering at this precision. Summing all 1000 terms with a power per
    term was correct and far too slow for a boundary analysis.
    """
    getcontext().prec = prec + 20
    if p is None:
        p = Decimal(2) ** (-Decimal(str(h)))
    q = Decimal(1) - p
    tiny = Decimal(10) ** (-(prec + 10))
    r = p / q
    # upper tail: P(X > m)
    hi = Decimal(0)
    j = m + 1
    if j <= N:
        t = Decimal(comb(N, j)) * p**j * q**(N - j)
        while j <= N:
            hi += t
            if t < tiny and j > m + 2:
                break
            t = t * Decimal(N - j) / Decimal(j + 1) * r
            j += 1
    # lower tail: P(X < n-m), walked DOWNWARD from n-m-1
    lo = Decimal(0)
    j = N - m - 1
    if j >= 0:
        t = Decimal(comb(N, j)) * p**j * q**(N - j)
        while j >= 0:
            lo += t
            if t < tiny and j < N - m - 3:
                break
            t = t * Decimal(j) / Decimal(N - j + 1) / r
            j -= 1
    getcontext().prec = prec
    return (hi + lo) + Decimal(0), hi + Decimal(0)

def cutoff(h, alpha, prec, majority_only=False):
    for m in range(N//2, N+1):
        t = tails(h, m, prec)[1 if majority_only else 0]
        if t <= alpha:
            return m
    return None

def crossing(m, alpha, prec, majority_only):
    """The H_I at which the tail for this m crosses alpha, or None if it never
    does on (0, 1].

    THE DOMAIN MATTERS, and the first version of this got it wrong. The
    two-sided tail is NOT monotone in H_I over an unrestricted range: it is
    minimised at p = 1/2, i.e. H_I = 1, and RISES again for H_I > 1 because the
    cell that was the minority becomes the majority. Bisecting on [0.3, 1.3]
    therefore converged on the spurious root above 1 and reported that every
    interval ran to the top of the range. At width 1 the domain is H_I <= 1 by
    definition, p lies in [1/2, 1), and on that domain the tail is strictly
    decreasing in H_I, so bisection is valid. Bound it there."""
    lo, hi = Decimal("0.05"), Decimal("1.0")
    idx = 1 if majority_only else 0
    # no crossing on the domain at all
    if tails(None, m, prec, p=Decimal(2) ** (-hi))[idx] > alpha:
        return None
    for _ in range(140):
        mid = (lo + hi) / 2
        t = tails(None, m, prec, p=Decimal(2) ** (-mid))[idx]
        if t > alpha:
            lo = mid        # tail still too big: need more entropy
        else:
            hi = mid
    return (lo + hi) / 2

def boundaries(h_lo, h_hi, alpha, prec):
    """Every H_I interval in [h_lo, h_hi] where the printed and exact cutoffs
    DISAGREE, found from the quantile boundaries rather than by sampling.

    The exact (two-sided) tail is strictly larger than the printed
    (majority-only) tail, so for each m the exact cutoff steps at a HIGHER H_I
    than the printed one, and the two differ exactly on the open interval
    between those two crossings."""
    out = []
    # Bisection at this precision resolves the crossing to far better than
    # 1e-18, so anything narrower than that is the SAME crossing reached from
    # two directions, not a disagreement. Reporting those as intervals would be
    # an instrument artefact dressed as a finding.
    RESOLUTION = Decimal("1e-18")
    for m in range(N // 2 + 20, N // 2 + 320):
        hp = crossing(m, alpha, prec, True)
        he = crossing(m, alpha, prec, False)
        if hp is None or he is None:
            continue
        a, b = min(hp, he), max(hp, he)
        if b - a < RESOLUTION:
            continue
        a = max(a, Decimal(str(h_lo))); b = min(b, Decimal(str(h_hi)))
        if b > a:
            out.append((m, a, b))
    return out

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--boundaries":
        h_lo = float(sys.argv[2]) if len(sys.argv) > 2 else 0.50
        h_hi = float(sys.argv[3]) if len(sys.argv) > 3 else 0.989
        print("Quantile-boundary analysis, n = %d, alpha = %s (3.1.4.3 step 1)." % (N, ALPHA_SPEC))
        print("Intervals of H_I in [%g, %g] where the PRINTED (majority-only) and" % (h_lo, h_hi))
        print("EXACT (two-sided) cutoffs DISAGREE. Not sampled: each endpoint is the")
        print("H_I at which that integer cutoff's tail crosses alpha, found by bisection.")
        print()
        iv = boundaries(h_lo, h_hi, ALPHA_SPEC, 40)
        if not iv:
            print("  none: the two cutoffs are identical throughout this range.")
        total = Decimal(0)
        for m, a, b in iv:
            total += (b - a)
            print("  cutoff %d: printed and exact differ for H_I in (%.16f, %.16f)  width %.3e"
                  % (m, float(a), float(b), float(b - a)))
        if iv:
            print()
            print("  %d interval(s); total measure %.4e of the %.4g-wide range (%.3f %%)."
                  % (len(iv), float(total), h_hi - h_lo, 100.0 * float(total) / (h_hi - h_lo)))
        sys.exit(0)
    hs = sys.argv[1:] or ["0.696"]
    a_sidak = sidak_alpha(60)
    print("n = %d   convention: cutoff = smallest m with P(X_max <= m) >= 1 - alpha;"
          " counts AT the cutoff pass" % N)
    print("alpha(spec)  = %s" % ALPHA_SPEC)
    print("alpha(Sidak) = %.17g   (1 - 0.99^(1/2000))" % float(a_sidak))
    print()
    hdr = "%-22s %8s %8s %8s %8s   %s" % ("H_I", "exact", "printed", "exact", "printed", "certification")
    print(hdr); print("%-22s %8s %8s %8s %8s" % ("", "(spec)", "(spec)", "(Sidak)", "(Sidak)"))
    bad = 0
    for h in hs:
        row = []
        for a in (ALPHA_SPEC, a_sidak):
            for mo in (False, True):
                row.append(cutoff(h, a, 60, majority_only=mo))
        c_spec, p_spec, c_sid, p_sid = row[0], row[1], row[2], row[3]
        # certify the SPEC exact value: the tail must straddle alpha at m and m-1,
        # and both computations must be stable when the precision is raised.
        t_at,  _ = tails(h, c_spec,     60)
        t_bel, _ = tails(h, c_spec - 1, 60)
        t_at2, _ = tails(h, c_spec,     120)
        t_bel2, _ = tails(h, c_spec - 1, 120)
        ok = (t_at <= ALPHA_SPEC < t_bel)
        stable = (abs(t_at - t_at2) < Decimal("1e-40") and abs(t_bel - t_bel2) < Decimal("1e-40"))
        cert = "OK" if (ok and stable) else "NOT CERTIFIED"
        if not (ok and stable): bad += 1
        print("%-22s %8d %8d %8d %8d   %s" % (h, c_spec, p_spec, c_sid, p_sid, cert))
        print("%-22s   tail(m)   = %.6e  <= alpha" % ("", float(t_at)))
        print("%-22s   tail(m-1) = %.6e  >  alpha   (margin ratio %.3g)"
              % ("", float(t_bel), float(t_bel / ALPHA_SPEC)))
        if c_spec != p_spec:
            print("%-22s   >>> the printed majority-only cutoff is %d, the exact is %d:"
                  " a DISAGREEMENT at this H_I" % ("", p_spec, c_spec))
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
