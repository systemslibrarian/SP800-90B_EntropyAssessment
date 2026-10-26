#!/usr/bin/env python3
"""OC-116: an independent high-precision oracle for P_local (SP 800-90B 6.3.7).

WHY THIS EXISTS. On saturated.bin this fork and two other implementations
disagree on Bitstring MultiMCW min-entropy by 2.3e-9, and the comparison alone
cannot say which is right -- three implementations is a vote, not an oracle.
The decomposition says where to look: the fork and the C99 port agree EXACTLY
on every integer and on P_global',

    C = 4337056    r = 81    N = 7999937    P_global' = 0.54258999794492346

and differ ONLY in P_local, which both obtain by BISECTION on a transcendental
equation evaluated in `long double`. So the disagreement is arithmetic, not
counting, and arbitrary-precision arithmetic settles it the way Levin's
representation settled C23 and NIST's worked example settled C22c.

THE EQUATION, as the production code states it (cpp/shared/utils.h:1087).
prediction_estimate_function(p, r, N) returns

    f(p) = ln(1 - p*x) - ln((r + 1 - r*x) * q) - (N + 1) * ln(x),   q = 1 - p

where x is the root of the fixed point

    x = 1 + q * p**r * x**(r + 1)

reached by iterating from x = 1 (monotone up, and the production code caps the
iteration at 66 steps with a `long double` epsilon stopping rule). calc_p_local
then bisects p until f(p) equals ln(0.99) to within relEpsilonEqual's 4-ulp
double tolerance.

This oracle solves the SAME equation with mpmath at 80 decimal digits, finding x
by a bracketed root-find in [1, 1/p] rather than by a capped iteration, and
locating p by bisection to a tolerance far below the quantity in dispute. It
implements no part of either tool.
"""
import sys
from mpmath import mp, mpf, log, findroot

mp.dps = 80

ALPHA = mpf('0.99')


def x_root(p, r):
    """The root of x = 1 + q*p^r*x^(r+1) in [1, 1/p], to full precision.

    The production code reaches this by iterating the recurrence from x = 1,
    which is monotone up and converges to the SMALLEST such root. Bracketing
    on [1, 1/p] and root-finding gets the same root without a step cap.
    """
    q = 1 - p
    g = lambda x: 1 + q * p**r * x**(r + 1) - x
    lo, hi = mpf(1), 1 / p
    glo = g(lo)                      # g(1) = q*p^r > 0
    # Walk hi down until the sign changes, then bisect. g(1/p) may be positive
    # when the root is interior, so the bracket is found rather than assumed.
    n = 0
    while g(hi) * glo > 0 and n < 400:
        hi = lo + (hi - lo) / 2
        n += 1
    if g(hi) * glo > 0:
        raise SystemExit("plocal_exact: no sign change bracketed for x; p=%s r=%d" % (mp.nstr(p, 20), r))
    for _ in range(400):
        mid = (lo + hi) / 2
        if g(mid) * glo > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def f(p, r, N):
    x = x_root(p, r)
    q = 1 - p
    return log(1 - p * x) - log((r + 1 - r * x) * q) - (N + 1) * log(x)


def solve_p_local(r, N, lo, hi=None):
    """Bisect f(p) = ln(alpha) for p. f is DECREASING in p over this domain,
    which is asserted rather than assumed."""
    target = log(ALPHA)
    lo = mpf(lo)
    hi = mpf(hi) if hi is not None else mpf(1) - mpf('1e-40')
    flo, fhi = f(lo, r, N), f(hi, r, N)
    if not (flo > target > fhi):
        raise SystemExit("plocal_exact: target not bracketed: f(lo)=%s target=%s f(hi)=%s"
                         % (mp.nstr(flo, 10), mp.nstr(target, 10), mp.nstr(fhi, 10)))
    for _ in range(300):
        mid = (lo + hi) / 2
        if f(mid, r, N) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    if len(sys.argv) >= 4:
        r, N, ldomain = int(sys.argv[1]), int(sys.argv[2]), mpf(sys.argv[3])
        cases = [('(command line)', r, N, ldomain, None, None)]
    else:
        # The disputed case, with both implementations' answers for comparison.
        cases = [('saturated.bin Bitstring MultiMCW', 81, 7999937,
                  mpf('0.54258999794492346'),
                  mpf('0.79162908359969442'),   # this fork
                  mpf('0.79162908233501794'))]  # the C99 port
    for label, r, N, ldom, fork, c99 in cases:
        p = solve_p_local(r, N, ldom)
        print("=" * 78)
        print("%s" % label)
        print("  r = %d   N = %d   ldomain = %s" % (r, N, mp.nstr(ldom, 17)))
        print("  ORACLE P_local      = %s" % mp.nstr(p, 25))
        print("  oracle min entropy  = %s" % mp.nstr(-log(p) / log(2), 25))
        if fork is None:
            continue
        for name, v in (('this fork', fork), ('C99 port', c99)):
            d = abs(v - p)
            print("  %-10s P_local = %s   |delta| = %s" % (name, mp.nstr(v, 17), mp.nstr(d, 6)))
        df, dc = abs(fork - p), abs(c99 - p)
        closer = 'this fork' if df < dc else ('the C99 port' if dc < df else 'a tie')
        print("  CLOSER TO THE ORACLE: %s  (ratio %s)"
              % (closer, mp.nstr(max(df, dc) / min(df, dc), 6)))


if __name__ == '__main__':
    main()


# ===========================================================================
# OC-116 part (c): IS THE long double FORMAT THE EXPLANATION?
#
# prediction_estimate_function computes x and the three logarithms in
# `long double`. That type is 53-bit on Apple arm64 and 64-bit (x87) on
# x86-64 -- the R-1 format difference. calc_p_local bisects p in `double`
# either way.
#
# So the production algorithm is EMULATED here at both inner precisions, with
# the same capped 66-step fixed point and the same 4-ulp stopping rule, and the
# results compared against the fork's measured arm64 value. If the 53-bit
# emulation lands on the fork's number and the 64-bit one lands near the
# oracle, the rows are platform behaviour and the attribution is settled.
# ===========================================================================

def emulate(r, N, ldomain, inner_bits, outer_bits=53, cap=66):
    """Re-run the production algorithm at a chosen inner precision."""
    from mpmath import mp as _mp
    target = None

    def inner(p):
        # prediction_estimate_function, at inner_bits
        old = _mp.prec
        _mp.prec = inner_bits
        try:
            pp = mpf(p)
            q = 1 - pp
            x = mpf(1)
            xlast = mpf(0)
            eps = mpf(2) ** (-(inner_bits - 1))
            i = 0
            while i <= cap and (x - xlast) > eps * x:
                xlast = x
                x = 1 + q * pp**r * x**(r + 1)
                i += 1
            return log(1 - pp * x) - log((r + 1 - r * x) * q) - (N + 1) * log(x)
        finally:
            _mp.prec = old

    old = _mp.prec
    _mp.prec = outer_bits
    try:
        target = log(mpf('0.99'))
        lo, hi = mpf(ldomain), mpf(1)
        p = (lo + hi) / 2
        for _ in range(1076):
            v = inner(p)
            if abs(v - target) <= 4 * abs(target) * mpf(2) ** (-(outer_bits - 1)):
                break
            if target < v:
                lo = p
            else:
                hi = p
            newp = (lo + hi) / 2
            if newp == p:
                break
            p = newp
        return p
    finally:
        _mp.prec = old


def part_c():
    r, N, ldom = 81, 7999937, mpf('0.54258999794492346')
    fork = mpf('0.79162908359969442')
    c99 = mpf('0.79162908233501794')
    oracle = solve_p_local(r, N, ldom)
    print()
    print("=" * 78)
    print("part (c): the production algorithm emulated at each long double precision")
    print("  oracle (80 dps)                      = %s" % mp.nstr(oracle, 22))
    print("  this fork, MEASURED on Apple arm64   = %s" % mp.nstr(fork, 22))
    print("  the C99 port, same machine           = %s" % mp.nstr(c99, 22))
    print()
    for bits, plat in ((53, 'Apple arm64 / MSVC: long double == double'),
                       (64, 'x86-64 x87: 64-bit significand')):
        e = emulate(r, N, ldom, bits)
        print("  emulated, inner %2d-bit  = %s" % (bits, mp.nstr(e, 22)))
        print("      |e - oracle| = %-12s   |e - fork| = %s"
              % (mp.nstr(abs(e - oracle), 6), mp.nstr(abs(e - fork), 6)))
        print("      %s" % plat)


if __name__ == '__main__' and '--part-c' in sys.argv:
    part_c()
