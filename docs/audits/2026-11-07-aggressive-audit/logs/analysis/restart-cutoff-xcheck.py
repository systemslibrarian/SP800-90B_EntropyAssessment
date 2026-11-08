#!/usr/bin/env python3
"""Independent cross-check of ea_restart's 3.1.4.3 cutoffs (audit 2026-11-07, restart component).

WHY THIS EXISTS. cpp/restart_main.cpp:maxCellCdf() and the fork's own oracle
(audits/2026-10-11-independent-audit/oracles/restart_multinomial_max.py) both use
Levin's representation in floating point. The oracle validates Levin against brute
force only at n <= 20. So the 32 pins in regression-restart.sh are the SAME
METHOD checked against itself at n = 1000 ("an oracle can verify its own copy").

This script uses a DIFFERENT method -- direct coefficient extraction from the
generating function, in 60-digit Decimal arithmetic:

    P(all cells <= m) = n! * [x^n]  prod_j  E_m(p_j x),      E_m(y) = sum_{i<=m} y^i / i!

with the same worst-case cell family the code uses (floor(1/p) cells at p plus
one remainder cell, remainder dropped when <= 1e-15, as restart_main.cpp:119-132).
It also recomputes 3.1.4.3 step 5 as printed (single Binomial(1000, p) tail) with
an exact Fraction for integer H_I and 60-digit Decimal otherwise.

Reads nothing from the tool. Compares against the pins the regression asserts the
tool prints (C23_PINS in cpp/selftest/regression-restart.sh, format H_I:deciding:printed).
"""
import math, sys, time
from decimal import Decimal, getcontext
from fractions import Fraction

getcontext().prec = 60
N = 1000
ALPHA = Decimal('0.000005')          # SP 800-90B 3.1.4.3 step 1
NFACT = Decimal(math.factorial(N))

PINS = """0.25:890:890 0.5:769:769 0.75:662:662 1:572:570 1.25:492:490
  1.5:423:421 1.75:366:362 2:316:312 2.25:273:269 2.5:236:232 2.75:205:200
  3:178:173 3.25:155:150 3.5:135:130 3.75:118:113 4:104:99 4.25:91:86
  4.5:80:76 4.75:71:66 5:63:58 5.25:56:51 5.5:50:45 5.75:45:40 6:40:36
  6.25:36:32 6.5:33:28 6.75:29:25 7:27:23 7.25:24:21 7.5:22:19 7.75:20:17
  8:19:15""".split()

# ------------------------------------------------------------------ cells, as the C++ forms them
def cells_like_cpp(H):
    """restart_main.cpp:117-120,132: p = 2^-H_I (long double); kfloor = floor(1/p);
    rem = 1 - kfloor*p, used only if > 1e-15. Mirrored in binary64 (= long double on arm64)."""
    p = 2.0 ** (-H)
    kfloor = int(math.floor(1.0 / p))
    rem = 1.0 - kfloor * p
    return p, kfloor, (rem if rem > 1e-15 else 0.0)

def p_exact(Hs):
    Hd = Decimal(Hs)
    if float(Hs).is_integer():
        return Fraction(1, 2 ** int(float(Hs))), Hd
    return None, Hd

# ------------------------------------------------------------------ printed binomial, step 5
def binom_pmf_decimal(p):
    q = 1 - p
    f = q ** N
    pmf = [f]
    for j in range(N):
        f = f * (N - j) / (j + 1) * p / q
        pmf.append(f)
    return pmf

def binom_pmf_fraction(p):
    q = 1 - p
    f = q ** N
    pmf = [f]
    for j in range(N):
        f = f * (N - j) / (j + 1) * p / q
        pmf.append(f)
    return pmf

def printed_cutoff(Hs):
    """largest x with P(X >= x) >= alpha (that x passes; x+1 fails) -- the code's convention
    at restart_main.cpp:81-85 and the spec's 'If Pr(X >= X_max) < alpha, the test fails'."""
    pf, Hd = p_exact(Hs)
    if pf is not None:
        pmf = binom_pmf_fraction(pf)
        a = Fraction(5, 10**6)
        tail = Fraction(0)
        for x in range(N, -1, -1):
            tail += pmf[x]
            if tail >= a:
                return x, pmf
        return 0, pmf
    p = Decimal(2) ** (-Hd)
    pmf = binom_pmf_decimal(p)
    tail = Decimal(0)
    for x in range(N, -1, -1):
        tail += pmf[x]
        if tail >= ALPHA:
            return x, pmf
    return 0, pmf

# ------------------------------------------------------------------ multinomial max via generating function
def exp_series(lam, m):
    a = [Decimal(0)] * (m + 1)
    a[0] = Decimal(1)
    for i in range(1, m + 1):
        a[i] = a[i - 1] * lam / i
    return a

def polymul_trunc(a, b, limit):
    out = [Decimal(0)] * (limit + 1)
    for i, ai in enumerate(a):
        if i > limit:
            break
        if not ai:
            continue
        jmax = min(len(b) - 1, limit - i)
        for j in range(jmax + 1):
            out[i + j] += ai * b[j]
    return out

def polypow_trunc(a, k, limit):
    result = [Decimal(1)]
    base = a
    while k:
        if k & 1:
            result = polymul_trunc(result, base, limit)
        k >>= 1
        if k:
            base = polymul_trunc(base, base, limit)
    return result

def maxcell_cdf_gf(Hs, m):
    """P(max cell count <= m) for the worst-case family, by GF coefficient extraction."""
    if m >= N:
        return Decimal(1)
    pf, Hd = p_exact(Hs)
    pd = Decimal(2) ** (-Hd) if pf is None else Decimal(pf.numerator) / Decimal(pf.denominator)
    _, kfloor, rem_f = cells_like_cpp(float(Hs))
    rem = (1 - kfloor * pd) if rem_f > 0.0 else Decimal(0)
    poly = polypow_trunc(exp_series(pd, m), kfloor, N)
    if rem > 0:
        poly = polymul_trunc(poly, exp_series(rem, m), N)
    coef = poly[N] if len(poly) > N else Decimal(0)
    return coef * NFACT

def twocell_cdf_closed(Hs, m):
    """For kfloor == 1 (H_I <= 1): max(N1, N2) <= m  <=>  N - m <= N1 <= m, N1 ~ Bin(N, p). Third method."""
    pf, Hd = p_exact(Hs)
    p = Decimal(2) ** (-Hd) if pf is None else Decimal(pf.numerator) / Decimal(pf.denominator)
    pmf = binom_pmf_decimal(p)
    lo = max(0, N - m)
    return sum(pmf[lo:m + 1])

def deciding_cutoff_gf(Hs, start):
    m = start
    while m < N and maxcell_cdf_gf(Hs, m) < 1 - ALPHA:
        m += 1
    return m

# ------------------------------------------------------------------ main
def main():
    t0 = time.time()
    print("restart-cutoff-xcheck: independent GF recomputation of the 3.1.4.3 cutoffs")
    print("alpha = %s, N = %d, Decimal prec = %d" % (ALPHA, N, getcontext().prec))
    print()
    print("%-7s %-5s %-5s %-5s | %-5s %-5s %-5s | %-9s %-9s | %s" % (
        "H_I", "kflr", "rem?", "prn", "pinP", "dec", "pinD", "cdf(d-1)", "cdf(d)", "verdict"))
    bad = 0
    for pin in PINS:
        Hs, pd_, pp_ = pin.split(":")
        pin_dec, pin_prn = int(pd_), int(pp_)
        p, kfloor, rem = cells_like_cpp(float(Hs))
        prn, _ = printed_cutoff(Hs)
        dec = deciding_cutoff_gf(Hs, prn)
        c_lo = maxcell_cdf_gf(Hs, dec - 1)
        c_hi = maxcell_cdf_gf(Hs, dec)
        ok = (prn == pin_prn) and (dec == pin_dec) and (c_lo < 1 - ALPHA <= c_hi)
        if kfloor == 1:
            # third method for the two-cell case
            t_lo = twocell_cdf_closed(Hs, dec - 1)
            t_hi = twocell_cdf_closed(Hs, dec)
            ok = ok and abs(t_lo - c_lo) < Decimal('1e-40') and abs(t_hi - c_hi) < Decimal('1e-40')
        bad += 0 if ok else 1
        print("%-7s %-5d %-5s %-5d | %-5d %-5d %-5d | %-9.3e %-9.3e | %s" % (
            Hs, kfloor, "yes" if rem > 0 else "no", prn, pin_prn, dec, pin_dec,
            float(1 - c_lo), float(1 - c_hi), "MATCH" if ok else "MISMATCH"))
    print()
    print("pins: %d checked, %d mismatches" % (len(PINS), bad))
    print()

    # --- accepted-by-fork / rejected-by-printed-text band at each pin
    print("Band of X_max values the fork ACCEPTS and 3.1.4.3 step 5 as printed REJECTS (the documented C23 divergence):")
    for pin in PINS:
        Hs, pd_, pp_ = pin.split(":")
        d, p_ = int(pd_), int(pp_)
        if d > p_:
            print("  H_I=%-5s  X_max in [%d, %d]  (%d values)" % (Hs, p_ + 1, d, d - p_))
        else:
            print("  H_I=%-5s  none (cutoffs coincide at %d)" % (Hs, d))
    print()

    # --- points named in the record
    print("Record points (not in the pin list):")
    for Hs, want_prn, want_dec, label in [
        ("0.696", 684, 684, "device operating point, width 1 (CLOSING-INVENTORY: both 684)"),
        ("0.9661822653793894", 581, 582, "OC-49 counterexample (printed 581, exact 582)"),
        ("0.888", None, None, "lowest H_I with any disagreement per CLOSING-INVENTORY (~0.888)"),
        ("0.887", None, None, "just below it"),
        ("1.584962500721156", None, None, "log2(3): kfloor boundary robustness (3 cells at 1/3 or 2 cells + remainder)"),
    ]:
        prn, _ = printed_cutoff(Hs)
        dec = deciding_cutoff_gf(Hs, prn)
        p, kfloor, rem = cells_like_cpp(float(Hs))
        note = ""
        if want_prn is not None:
            note = "  expected printed %d deciding %d -> %s" % (want_prn, want_dec, "MATCH" if (prn, dec) == (want_prn, want_dec) else "MISMATCH")
        print("  H_I=%-20s kfloor=%d rem=%.3g  printed=%d deciding=%d%s  [%s]" % (Hs, kfloor, rem, prn, dec, note, label))
    print()

    # --- the binary64 rounding band where p == 1.0 exactly (both cutoffs 1000; both gates vacuous)
    print("binary64 (= long double on Darwin arm64) rounding of p = 2^-H_I to exactly 1.0 (restart_main.cpp:77,118 return n / 0):")
    for H in ["1e-300", "1e-20", "1e-17", "1.0e-16", "1.6e-16", "2e-16", "1e-15"]:
        p = 2.0 ** (-float(H))
        print("  H_I=%-8s  2^-H_I == 1.0 in binary64: %s   (p = %.17g)" % (H, p == 1.0, p))
    # and the H_I below which the printed cutoff is 1000 regardless of rounding: p^1000 >= alpha
    Hstar = -math.log2(float(ALPHA) ** (1.0 / N))
    print("  H_I below which P(X >= 1000) = p^1000 >= alpha, i.e. cutoff 1000 by the statistic itself: H_I < %.6g" % Hstar)
    print()
    print("elapsed %.1f s" % (time.time() - t0))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
