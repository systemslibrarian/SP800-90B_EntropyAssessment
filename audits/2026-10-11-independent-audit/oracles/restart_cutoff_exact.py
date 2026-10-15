#!/usr/bin/env python3
"""Exact SP 800-90B 3.1.4.3 sanity-check cutoff, for OC-7.

The standard gives a closed form, not a method:

  1. Let p = 2^-H_I. Let alpha be 0.000005.
  5. Calculate P(X >= X_max) = sum_{j=X_max}^{1000} C(1000,j) p^j (1-p)^(1000-j).
     If Pr(X >= X_max) < alpha, the test fails. Otherwise, the test passes.

So the largest count that PASSES is (smallest c with P(X>=c) < alpha) - 1, which
is the convention ea_restart's X_cutoff uses ("Counts equal to this value should
pass. Larger values should fail.").

The tool instead takes an empirical order statistic of 5,000,000 simulated
experiments. This script is the reference the tool is compared against in OC-7.

alpha: the tool computes 1 - 0.99^(1/(r+c)) = 5.0251553006155243e-06, the exact
Sidak value for 2000 experiments, where the standard prints the Bonferroni
approximation 0.000005. Both give identical cutoffs at every H_I in 1..8.
"""
import sys
from mpmath import mp, mpf, binomial, power, log

mp.dps = 60
N = 1000

def alpha_tool(r=1000, c=1000):
    return 1 - mp.e ** (mp.log(mpf('0.99')) / (r + c))

def tail(x, p):
    return sum(binomial(N, j) * power(p, j) * power(1 - p, N - j) for j in range(x, N + 1))

def exact_cutoff(H_I, alpha):
    """Largest count that passes, matching ea_restart's X_cutoff convention."""
    p = power(2, -mpf(H_I))
    lo, hi = 1, N
    while lo < hi:
        mid = (lo + hi) // 2
        if tail(mid, p) < alpha: hi = mid
        else: lo = mid + 1
    return lo - 1

if __name__ == '__main__':
    a = alpha_tool()
    hs = sys.argv[1:] or ['1', '2', '3', '4', '5', '6', '7', '7.5', '8']
    print('alpha = %.17g' % float(a))
    print('%-6s %-8s %-14s %s' % ('H_I', 'cutoff', 'P(X>=cut+1)', 'entropy at cutoff'))
    for H in hs:
        c = exact_cutoff(H, a)
        p = power(2, -mpf(H))
        print('%-6s %-8d %-14.4e %.6f bit' % (H, c, float(tail(c + 1, p)), float(-log(mpf(c)/N, 2))))
