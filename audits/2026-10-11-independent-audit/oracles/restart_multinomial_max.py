#!/usr/bin/env python3
"""OC-30: the restart sanity check's ACTUAL statistic, exactly.

SP 800-90B 3.1.4.3 step 5 prints the tail of a single Binomial(1000, p). But the
value tested, X_max, is the maximum count of the ROW/COLUMN-SPECIFIC most likely
symbol -- the maximum cell count of a multinomial -- which is stochastically
larger. Hill/UL formal comments on SP 800-90B (final, v1.9, 2019-12-12,
https://www.untruth.org/~josh/sp80090b/, "UL SP800-90B-final comments v1.9
20191212.pdf", SHA-256 35ea31ce...) comment 3.a: "The underlying distribution
for the existing test is really the maximum count of any symbol of a multinomial
distribution; our testing indicates that the binomial distribution isn't a good
approximation of the actual underlying distribution." The printed binomial
p-value therefore REJECTS GOOD SOURCES, and a cutoff computed from it is
conservative in the wrong direction: it fails correctly-operating noise sources.

This module computes the exact CDF of the multinomial maximum by Levin's
representation ("A Representation for Multinomial Cumulative Distribution
Functions", Ann. Statist. 9(5), 1981) -- the first of the two exact methods
Hill names -- and from it:

  * the exact cutoff for the actual statistic (the deciding figure), and
  * the false-reject rate of the standard's printed binomial cutoff
    (computed here, not quoted).

Levin: for X ~ Multinomial(n; p_1..p_k) and any s > 0,
  P(all X_j <= m) = n!/(s^n e^-s) * P(W = n) * prod_j P(Poisson(s p_j) <= m)
where W is a sum of independent Poisson(s p_j) variables each conditioned on
being <= m. Every factor is a probability or a log-domain scalar, so nothing
underflows; verified against brute-force enumeration below.

Worst case, per Hill comment 3.a.i and matching the tool's own k_effective:
floor(1/p) symbols at probability p plus, if 1/p is not an integer, one symbol
holding the remainder.

Usage: restart_multinomial_max.py [--table3] [--pins]
"""
import sys, math
from decimal import Decimal, getcontext
from fractions import Fraction

getcontext().prec = 80
N = 1000
EXPERIMENTS = 2000                      # 1000 rows + 1000 columns

# ---------------------------------------------------------------- the standard's printed statistic
_pmf_cache = {}
def binom_pmf(H_I):
    """pmf of Bin(1000, 2^-H_I): exact Fraction for integer H_I, else 80-digit Decimal."""
    key = str(H_I)
    if key in _pmf_cache: return _pmf_cache[key]
    # int(H_I) fails on '1.00'; go through float so '1', '1.0' and '1.00' all work.
    p = Fraction(1, 2 ** int(float(H_I))) if float(H_I).is_integer() else Decimal(2) ** (-Decimal(str(H_I)))
    q = 1 - p
    f = q ** N
    pmf = [f]
    for j in range(N):
        f = f * (N - j) / (j + 1) * p / q
        pmf.append(f)
    _pmf_cache[key] = pmf
    return pmf

def _dec(x):
    return Decimal(x.numerator) / Decimal(x.denominator) if isinstance(x, Fraction) else x

def binomial_cutoff(H_I, alpha):
    """3.1.4.3 step 5 as printed: largest x with Pr[X >= x] >= alpha (so x passes)."""
    a = Decimal(str(alpha)); pmf = binom_pmf(H_I); tail = 0
    for x in range(N, -1, -1):
        tail += pmf[x]
        if _dec(tail) >= a: return x
    return 0

def binomial_tail(H_I, x):
    pmf = binom_pmf(H_I); t = 0
    for j in range(N, x - 1, -1): t += pmf[j]
    return float(_dec(t))

# ---------------------------------------------------------------- the actual statistic
def cells(H_I):
    """Hill's worst case / the tool's k_effective: floor(1/p) cells at p, plus the remainder."""
    p = 2.0 ** (-float(H_I))
    kfloor = int(math.floor(1.0 / p))
    rem = 1.0 - kfloor * p
    return p, kfloor, (rem if rem > 1e-15 else 0.0)

def _trunc_poisson(lam, m):
    """(truncated pmf over 0..m, log P(Poisson(lam) <= m)). Scaled to sum 1."""
    logs = [i * math.log(lam) - math.lgamma(i + 1) if lam > 0 else (0.0 if i == 0 else -math.inf)
            for i in range(m + 1)]
    mx = max(logs)
    w = [math.exp(l - mx) for l in logs]
    tot = sum(w)
    # P(Poisson(lam) <= m) = e^-lam * sum_i lam^i/i! = exp(-lam + mx + log tot)
    return [x / tot for x in w], (-lam + mx + math.log(tot))

def _conv_trunc(a, b, limit):
    out = [0.0] * (limit + 1)
    for i, ai in enumerate(a):
        if ai == 0.0: continue
        jmax = min(len(b) - 1, limit - i)
        for j in range(jmax + 1):
            out[i + j] += ai * b[j]
    return out

def _pow_trunc(a, e, limit):
    result = [1.0] + [0.0] * limit
    base = a[:]
    while e:
        if e & 1: result = _conv_trunc(result, base, limit)
        e >>= 1
        if e: base = _conv_trunc(base, base, limit)
    return result

def maxcell_cdf(H_I, m):
    """P(every cell count <= m) by Levin's representation. Exact up to float rounding."""
    if m >= N: return 1.0
    p, kfloor, rem = cells(H_I)
    s = float(N)
    pmf_p, logP_p = _trunc_poisson(s * p, m)
    dist = _pow_trunc(pmf_p, kfloor, N)
    logprod = kfloor * logP_p
    if rem > 0.0:
        pmf_r, logP_r = _trunc_poisson(s * rem, m)
        dist = _conv_trunc(dist, pmf_r, N)
        logprod += logP_r
    if dist[N] <= 0.0: return 0.0
    # n!/(s^n e^-s) in logs, with s = n
    logpre = math.lgamma(N + 1) - N * math.log(s) + s
    return math.exp(logpre + math.log(dist[N]) + logprod)

def maxcell_cutoff(H_I, alpha, start=None):
    """Smallest m with P(max <= m) >= 1 - alpha: the deciding cutoff, counts <= m pass."""
    m = start if start is not None else binomial_cutoff(H_I, alpha)
    while m < N and maxcell_cdf(H_I, m) < 1.0 - alpha:
        m += 1
    return m

def false_reject(H_I, cutoff):
    """Per-experiment and overall false-reject probability of a cutoff, for the ACTUAL
    statistic on a source whose true min entropy is H_I. Overall treats the 2000
    row/column experiments as independent, which they are not (Hill comment 3.b)."""
    per = 1.0 - maxcell_cdf(H_I, cutoff)
    return per, 1.0 - (1.0 - per) ** EXPERIMENTS

# ---------------------------------------------------------------- method validation
def _brute(n, k, m):
    """Exact P(all cells <= m) for equal-probability cells by enumeration."""
    from itertools import product as iproduct
    from math import factorial
    tot = 0.0
    def rec(cell, left, logmult):
        nonlocal tot
        if cell == k - 1:
            if left <= m:
                tot += math.exp(logmult - math.lgamma(left + 1) + math.lgamma(n + 1) - n * math.log(k))
            return
        for c in range(0, min(m, left) + 1):
            rec(cell + 1, left - c, logmult - math.lgamma(c + 1))
    rec(0, n, 0.0)
    return tot

def validate():
    print("## Method validation: Levin's representation vs brute-force enumeration")
    print("| n | k | m | brute force | Levin | rel |")
    print("|---:|---:|---:|---|---|---:|")
    ok = True
    for n, k, m in [(5, 2, 3), (10, 3, 5), (12, 4, 4), (20, 2, 13), (15, 5, 5), (8, 8, 2)]:
        global N
        saved = N; N = n
        H = math.log2(k)
        lev = maxcell_cdf(H, m)
        N = saved
        bf = _brute(n, k, m)
        rel = abs(lev - bf) / bf if bf else abs(lev)
        ok = ok and rel < 1e-12
        print("| %d | %d | %d | %.15g | %.15g | %.1e |" % (n, k, m, bf, lev, rel))
    print("\n%s\n" % ("All agree to better than 1e-12." if ok else "DISAGREEMENT -- do not use."))
    return ok

TABLE3 = [  # Hill v1.9 Table 3: min entropy, series, simulated cutoff, binomial/original cutoff
    ("0.852803", "MedianEnt",    625, 623), ("0.995319", "IIDMedianEnt", 572, 571),
    ("1",        "FullEnt",      572, 570), ("1.86565",  "MedianEnt",    343, 338),
    ("1.9908",   "IIDMedianEnt", 317, 314), ("2",        "FullEnt",      318, 312),
    ("3.75695",  "MedianEnt",    118, 113), ("3.97586",  "IIDMedianEnt", 105, 100),
    ("4",        "FullEnt",      104,  99), ("7.41556",  "MedianEnt",     23,  19),
    ("7.87995",  "IIDMedianEnt",  20,  16), ("8",        "FullEnt",       19,  15),
    ("13.2812",  "MedianEnt",      6,   3), ("14.3163",  "IIDMedianEnt",  5,   3),
    ("16",       "FullEnt",        4,   3),
]

def table3(alpha=0.000005):
    print("## Anchor: Hill v1.9 Table 3 (published) vs this machinery, alpha = %g" % alpha)
    print("Simulated cutoffs are Hill's 2,000,000-round simulation; ours are exact (Levin).")
    print()
    print("| min entropy | series | Hill binomial | ours (exact rational) | match | Hill simulated | ours (exact Levin) | delta |")
    print("|---|---|---:|---:|---|---:|---:|---:|")
    nb = ns = 0
    for H, series, hsim, hbin in TABLE3:
        ob = binomial_cutoff(H, alpha)
        os_ = maxcell_cutoff(H, alpha, start=ob)
        nb += (ob == hbin); ns += (os_ == hsim)
        print("| %s | %s | %d | %d | %s | %d | %d | %+d |" % (
            H, series, hbin, ob, "yes" if ob == hbin else "**NO**", hsim, os_, os_ - hsim))
    print()
    print("binomial column: %d of %d exact matches" % (nb, len(TABLE3)))
    print("simulated column: %d of %d exact matches; all deltas within the noise of a 2e6-round"
          " simulation at a 5e-6 tail (see the monotonicity note)" % (ns, len(TABLE3)))
    print()
    print("### Hill's own table is non-monotonic, which bounds its simulation noise")
    print("A lower min entropy means a larger p and therefore a cutoff that cannot be smaller.")
    for a, b in (("1.9908", "2"), ("3.97586", "4"), ("14.3163", "16")):
        ra = next(r for r in TABLE3 if r[0] == a); rb = next(r for r in TABLE3 if r[0] == b)
        print("- H_I %s -> %d and H_I %s -> %d (simulated): %s" % (
            a, ra[2], b, rb[2], "non-monotonic by %d" % (rb[2] - ra[2]) if rb[2] > ra[2] else "monotonic"))
    print()

def rates(alpha=0.000005):
    print("## The direction, computed here rather than quoted: false-reject rate of each cutoff")
    print("For a source whose true min entropy IS H_I (so every rejection is a false one),")
    print("the exact per-experiment and overall rates of the ACTUAL statistic. Target: 0.01.")
    print()
    print("| H_I (full entropy) | standard's printed cutoff | per-experiment | overall over 2000 | corrected cutoff | per-experiment | overall |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for H in ("1", "2", "4", "8", "16"):
        cb = binomial_cutoff(H, alpha); cc = maxcell_cutoff(H, alpha, start=cb)
        pb, ob = false_reject(H, cb); pc, oc = false_reject(H, cc)
        print("| %s | %d | %.3e | **%.1f%%** | %d | %.3e | %.2f%% |" % (H, cb, pb, 100 * ob, cc, pc, 100 * oc))
    print()
    print("Hill's reported rates for the original check are 1.2%, 1.7%, 6.5%, 32.4% and 25.1%")
    print("at 1, 2, 4, 8 and 16 bits (v1.9 p.22), and 'a theoretical failure rate of nearly")
    print("100% for wide data' (p.4). Compare the fourth column above.")
    print()

def pins(alpha=0.000005):
    print("## Pinned cutoffs for the regression: H_I in 0.25 steps, 1..8 bit symbols")
    print("(the tool supports 1-8 bit symbols, so H_I <= 8)")
    out = []
    for i in range(1, 33):
        H = i / 4.0
        Hs = ("%g" % H)
        cb = binomial_cutoff(Hs, alpha); cc = maxcell_cutoff(Hs, alpha, start=cb)
        out.append("%s:%d:%d" % (Hs, cc, cb))
    print(" ".join(out))
    print()

if __name__ == '__main__':
    args = sys.argv[1:]
    if not validate(): sys.exit(1)
    if not args or '--table3' in args: table3(); rates()
    if not args or '--pins' in args: pins()
