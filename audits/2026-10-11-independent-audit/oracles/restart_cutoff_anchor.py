#!/usr/bin/env python3
"""Anchor for C23 (OC-27): is restart_cutoff_exact.py's "exact" cutoff actually the
standard's number?  Two independent computations that share NOTHING with that
script or with the tool:

  1. STANDARD's statistic, exact rational arithmetic.  X ~ Binomial(1000, p),
     p = 2^-H_I.  For integer H_I, p is a dyadic rational and fractions.Fraction
     gives Pr[X >= x] EXACTLY (no floating point anywhere); the pmf is built by
     the multiplicative recurrence f(j+1) = f(j) (N-j)/(j+1) p/q from f(0) = q^N,
     never through binomial coefficients.  For non-integer H_I the same
     recurrence runs in decimal.Decimal at 80 digits.
     cutoff = largest x with Pr[X >= x] >= alpha   (3.1.4.3: fail iff Pr < alpha)

  2. TOOL's statistic, exact.  restart_main.cpp simulateCount() draws 1000
     symbols over k_eff = ceil(1/p) cells -- floor(1/p) cells at probability p
     and, if 1/p is not an integer, one cell with the remainder -- and returns
     the MAX count over all cells.  Pr[max <= m] = N! [x^N] prod_j S_m(p_j x),
     S_m(y) = sum_{i<=m} y^i/i!, computed exactly to 40 digits by truncated
     polynomial powering.  The tool's quantile rule is
     results[floor((1-alpha) R) - 1] over R sorted simulated maxima, i.e. the
     smallest m with Pr[max <= m] >= 1 - alpha, up to simulation noise.

Usage: restart_cutoff_anchor.py [sweep-log-dir]    (logs from ea_restart -v)
"""
import sys, os, re, glob
from fractions import Fraction
from decimal import Decimal, getcontext
from mpmath import mp, mpf, factorial
getcontext().prec = 80
mp.dps = 40
N = 1000

def alpha_tool():
    # 1 - 0.99^(1/2000), the tool's own Sidak alpha, at 80 digits
    return Decimal(1) - Decimal("0.99") ** (Decimal(1) / Decimal(2000))

_pmf_cache = {}
def binom_pmf_exact(H_I):
    """pmf of Bin(1000, 2^-H_I) by the multiplicative recurrence; Fraction for integer H_I, Decimal otherwise."""
    if H_I in _pmf_cache: return _pmf_cache[H_I]
    if float(H_I).is_integer():
        p = Fraction(1, 2 ** int(H_I))
    else:
        p = Decimal(2) ** (-Decimal(str(H_I)))
    q = 1 - p
    f = q ** N
    pmf = [f]
    for j in range(N):
        f = f * (N - j) / (j + 1) * p / q
        pmf.append(f)
    _pmf_cache[H_I] = pmf
    return pmf

def binom_tail_exact(H_I, x):
    """Pr[X >= x], summed from the top down."""
    pmf = binom_pmf_exact(H_I)
    t = 0
    for j in range(N, x - 1, -1): t += pmf[j]
    return t

def standard_cutoff(H_I, alpha):
    a = Decimal(alpha) if not isinstance(alpha, Decimal) else alpha
    pmf = binom_pmf_exact(H_I)
    tail = 0; x = N
    while x >= 0:                      # walk down: tail(x) grows; stop at the first x with tail >= alpha
        tail += pmf[x]
        td = Decimal(tail.numerator) / Decimal(tail.denominator) if isinstance(tail, Fraction) else tail
        if td >= a: return x           # largest x with Pr[X >= x] >= alpha
        x -= 1
    return 0

def poly_mul(a, b, deg):
    out = [mpf(0)] * (deg + 1)
    for i, ai in enumerate(a):
        if ai == 0: continue
        for j in range(min(len(b), deg + 1 - i)):
            out[i + j] += ai * b[j]
    return out

def poly_pow(a, e, deg):
    result = [mpf(1)] + [mpf(0)] * deg
    base = a[:]
    while e:
        if e & 1: result = poly_mul(result, base, deg)
        e >>= 1
        if e: base = poly_mul(base, base, deg)
    return result

def tool_model_cdf(H_I, m):
    """Pr[max over k_eff cells <= m], exact to mp.dps."""
    p = mpf(2) ** (-mpf(str(H_I)))
    kfloor = int(mp.floor(1 / p)); rem = 1 - kfloor * p
    S = lambda pj: [pj ** i / factorial(i) for i in range(m + 1)]
    poly = poly_pow(S(p), kfloor, N)
    if rem > mpf(10) ** -30:
        poly = poly_mul(poly, S(rem), N)
    return poly[N] * factorial(N)

def tool_model_cutoff(H_I, alpha):
    a = mpf(str(alpha))
    m = standard_cutoff(H_I, alpha)    # the max over cells is at least the single binomial, so start here and step up
    while tool_model_cdf(H_I, m) < 1 - a:
        m += 1
    return m

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from restart_cutoff_exact import exact_cutoff, alpha_tool as alpha_tool_mp
    measured = {}
    if len(sys.argv) > 1:
        for f in sorted(glob.glob(os.path.join(sys.argv[1], '*.log'))):
            t = open(f).read()
            h = re.search(r'^H_I:\s*([0-9.]+)', t, re.M); c = re.search(r'X_cutoff:\s*(\d+)', t)
            if h and c: measured.setdefault(float(h.group(1)), []).append(int(c.group(1)))
    HS = [1, 2, 3, 4, 5, 6, 7, 7.5, 8]
    a_tool = alpha_tool()
    print("alpha_tool = %s (80-digit decimal); restart_cutoff_exact's alpha = %.17g" % (str(a_tool)[:24], float(alpha_tool_mp())))
    print()
    print("## Anchor 1: standard's binomial cutoff, Fraction/Decimal recurrence vs restart_cutoff_exact.py (mpmath binomial)")
    print("| H_I | anchor (exact rational) | restart_cutoff_exact | agree | Pr[X >= cutoff+1] |")
    print("|---:|---:|---:|---|---:|")
    for H in HS:
        c1 = standard_cutoff(H, a_tool); c2 = exact_cutoff(H, alpha_tool_mp())
        t = binom_tail_exact(H, c1 + 1); td = float(t)
        print("| %s | %d | %d | %s | %.3e |" % (H, c1, c2, 'yes' if c1 == c2 else 'NO', td))
    print()
    for alpha, label in ((a_tool, "alpha_tool = 1 - 0.99^(1/2000)"), (Decimal("0.000005"), "alpha = 0.000005 (the standard's printed Bonferroni)"), (Decimal("0.001"), "alpha = 0.001 (illustrative, 200x looser)")):
        print("## %s" % label)
        print("| H_I | k_eff | standard cutoff (single binomial) | tool-statistic cutoff (max over k_eff cells, exact) | gap | tool measured (simulation) |")
        print("|---:|---:|---:|---:|---:|---|")
        for H in HS:
            p = 2 ** (-float(H)); keff = -(-1 // p) if False else int(-(-1.0 / p // 1))
            cs = standard_cutoff(H, alpha); ct = tool_model_cutoff(H, alpha)
            meas = ', '.join(str(v) for v in measured.get(float(H), [])) if alpha == a_tool else '-'
            print("| %s | %d | %d | %d | %+d | %s |" % (H, keff, cs, ct, ct - cs, meas or '-'))
        print()
    print("done")
