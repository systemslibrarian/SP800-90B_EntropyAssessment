#!/usr/bin/env python3
"""OC-121: does r = 1 admit an in-domain root, and what is K's integrand there?

WHY. C22a = c * K is the constant every entropy figure in this project
subtracts. K = 1.6189e-14 was taken as the sup of

    2^-52 / ( |f'(p*)| * p* * ln 2 )

over an (N, r, ldomain) sweep, ATTAINED AT N = 5, r = 2 -- and r = 2 is the
FIRST value in that sweep's r-list. r = 1 was never examined, and the sweep's
definition is not in this repository: only its two outputs survive.

THE GRID IS NOT RECOVERED. The domain is taken from the mathematics instead:

  * p is a probability and calc_p_local's own assertion says it is >= 1/k, so
    the domain is  p in [1/k, 1)  with k the alphabet size, 2 <= k <= 256.
    cpp/shared/utils.h:1089 and c22_bound.cpp:70 both state the 1/k floor.
  * r is max_run_len + 1 (utils.h:1234 passes max_run_len+1), so r = 1 means
    the longest run of correct predictions is ZERO -- which happens whenever no
    prediction is ever correct, and is therefore reachable, not hypothetical.
  * f(p) = ln(1 - p x) - ln((r+1 - r x) q) - (N+1) ln(x), q = 1-p, x the root
    of x = 1 + q p^r x^(r+1), exactly as prediction_estimate_function states it.

For each (r, N, k) this reports whether f(p) = ln(0.99) has a root in [1/k, 1)
and, if so, the integrand there. Everything is mpmath at 60 digits; this
implements no part of the tool.
"""
import sys, itertools
from mpmath import mp, mpf, log
mp.dps = 60
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from plocal_exact import x_root, f as fval

LN2 = log(2)
EPS = mpf(2) ** -52
TARGET = log(mpf('0.99'))
K_RECORDED = mpf('1.6189e-14')


def root_in_domain(r, N, lo):
    """The root of f(p) = ln(0.99) in [lo, 1), or None if there is none.

    f is monotone DECREASING in p over this domain, which is checked rather
    than assumed: if f(lo) is already below the target there is no root at or
    above lo, and if f near 1 is above it there is none below 1 either.
    """
    hi = mpf(1) - mpf('1e-30')
    try:
        flo, fhi = fval(lo, r, N), fval(hi, r, N)
    except Exception:
        return None, 'f undefined at an endpoint'
    if flo < TARGET:
        return None, 'f(1/k)=%s < target: root is BELOW the domain' % mp.nstr(flo, 6)
    if fhi > TARGET:
        return None, 'f(1-)=%s > target: root is ABOVE the domain' % mp.nstr(fhi, 6)
    a, b = lo, hi
    for _ in range(250):
        m = (a + b) / 2
        if fval(m, r, N) > TARGET:
            a = m
        else:
            b = m
    return (a + b) / 2, 'in domain'


def integrand(p, r, N):
    h = mpf('1e-28')
    d = (fval(p + h, r, N) - fval(p - h, r, N)) / (2 * h)
    if d == 0:
        return None, d
    return EPS / (abs(d) * p * LN2), d


def main():
    rs = [1, 2, 3, 4]
    Ns = [5, 6, 8, 10, 20, 100, 1000, 10000, 1000000]
    ks = [2, 4, 16, 256]
    print('K as recorded: %s   (attained at N=5, r=2)' % mp.nstr(K_RECORDED, 6))
    print('domain: p in [1/k, 1),  k in %s   (utils.h:1089, c22_bound.cpp:70)' % ks)
    print()
    print('%-3s %-9s %-5s %-24s %-13s %-12s %s' % ('r', 'N', 'k', 'p*', "|f'(p*)|", 'integrand', 'vs K'))
    best = None
    inrange = 0
    for r, N, k in itertools.product(rs, Ns, ks):
        lo = mpf(1) / k
        p, why = root_in_domain(r, N, lo)
        if p is None:
            continue
        inrange += 1
        val, d = integrand(p, r, N)
        if val is None:
            continue
        tag = '*** EXCEEDS ***' if val > K_RECORDED else '%.3fx' % float(val / K_RECORDED)
        if best is None or val > best[0]:
            best = (val, r, N, k, p)
        print('%-3d %-9d %-5d %-24s %-13s %-12s %s'
              % (r, N, k, mp.nstr(p, 18), mp.nstr(abs(d), 6), mp.nstr(val, 6), tag))
    print()
    print('(r, N, k) combinations with an in-domain root: %d of %d'
          % (inrange, len(rs) * len(Ns) * len(ks)))
    if best:
        print('largest integrand found: %s at r=%d, N=%d, k=%d'
              % (mp.nstr(best[0], 8), best[1], best[2], best[3]))
        print('  ratio to the recorded K: %s' % mp.nstr(best[0] / K_RECORDED, 6))
    # And the question asked directly: does r = 1 have ANY in-domain root?
    print()
    print('r = 1, every N and k tried:')
    any1 = False
    for N, k in itertools.product(Ns, ks):
        p, why = root_in_domain(1, N, mpf(1) / k)
        if p is not None:
            any1 = True
            v, _ = integrand(p, 1, N)
            print('  N=%-8d k=%-4d ROOT %s  integrand %s' % (N, k, mp.nstr(p, 18), mp.nstr(v, 6)))
    if not any1:
        p, why = root_in_domain(1, 5, mpf(1) / 2)
        print('  NO in-domain root at any (N, k) tried. Representative reason at N=5, k=2:')
        print('    %s' % why)


if __name__ == '__main__':
    main()
