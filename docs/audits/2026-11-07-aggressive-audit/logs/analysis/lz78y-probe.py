#!/usr/bin/env python3
"""Analysis-phase probes for SP 800-90B section 6.3.10 (LZ78Y), written FROM THE
SPEC TEXT (reference/sp800-90b.pages.txt, PDF pp. 63-65), not from cpp/.

Probe A: does the transcription of steps 1-3 reproduce the worked example?
         (S = 2,1,3,2,1,3,1,3,1,2,1,3,2; B = 4; expected correct = 0,0,1,1,0,1,1,0;
          P_global = 0.5, P_global' = 0.9868, P_local = 0.1229, H = 0.0191)
         Two readings of step 3.a are tried: (i)/(ii) SEQUENTIAL (add with 0 then
         increment -> net 1) and (i)/(ii) EXCLUSIVE (add with 0 and stop).
Probe B: F08 -- x = x_10 (spec, step 5) against x iterated to convergence.
         Direction and magnitude of the P_local difference at compliant N.
Probe C: is f(p) = ln[(1-px)/((r+1-rx)q)] - (N+1) ln x monotone decreasing in p on
         (1/k, r/(r+1))?  The tool-independent question behind any "P_local cannot
         affect the result" shortcut and behind a bracketed bisection.
Output: everything is printed; the caller redirects to a log file.
"""
import math, sys

try:
    from mpmath import mp, mpf, log, sqrt
    mp.dps = 60
    HAVE_MP = True
except ImportError:  # pragma: no cover
    HAVE_MP = False

# ---------------------------------------------------------------- spec steps 1-3
def lz78y_spec(S, B, max_dict=65536, sequential=True):
    """Return (correct list, dictionary size).  S is 1-indexed in the standard;
    here S[0] is s_1.  `sequential` selects the reading of step 3.a.i/ii."""
    L = len(S)
    N = L - B - 1
    s = lambda t: S[t - 1]           # s_t, 1-indexed
    correct = [0] * N
    D = {}
    size = 0
    for i in range(B + 2, L + 1):
        # 3.a  for j = B down to 1
        for j in range(B, 0, -1):
            prev = tuple(s(t) for t in range(i - j - 1, i - 1))   # s_{i-j-1} .. s_{i-2}
            y = s(i - 1)
            added = False
            if prev not in D and size < max_dict:               # 3.a.i
                D[prev] = {y: 0}
                size += 1
                added = True
            if prev in D and (sequential or not added):          # 3.a.ii
                D[prev][y] = D[prev].get(y, 0) + 1
        # 3.b
        prediction = None
        maxcount = 0
        for j in range(B, 0, -1):
            prev = tuple(s(t) for t in range(i - j, i))           # s_{i-j} .. s_{i-1}
            if prev in D:
                best = max(D[prev].values())
                y = max(yy for yy, c in D[prev].items() if c == best)   # tie -> higher value
                if D[prev][y] > maxcount:
                    prediction = y
                    maxcount = D[prev][y]
        # 3.c
        if prediction is not None and prediction == s(i):
            correct[i - B - 2] = 1       # correct_{i-B-1}, 1-indexed -> 0-indexed
    return correct, size

def longest_run(bits):
    best = cur = 0
    for b in bits:
        cur = cur + 1 if b else 0
        best = max(best, cur)
    return best

# ---------------------------------------------------------------- spec steps 4-6
def x_iter(p, r, iters):
    q = 1 - p
    x = p * 0 + 1
    for _ in range(iters):
        x = 1 + q * p ** r * x ** (r + 1)
    return x

def x_conv(p, r, cap=10000):
    q = 1 - p
    x = p * 0 + 1
    for _ in range(cap):
        xn = 1 + q * p ** r * x ** (r + 1)
        if xn == x:
            break
        x = xn
    return x

def f_of(p, r, N, xfun):
    q = 1 - p
    x = xfun(p, r)
    a = 1 - p * x
    b = (r + 1 - r * x) * q
    if a <= 0 or b <= 0 or x <= 0:
        return None
    return log(a) - log(b) - (N + 1) * log(x)

def p_local(r, N, lo, xfun, ln_alpha, steps=200):
    """Bisection for f(p) = ln 0.99 on [lo, 1).  Returns None when f(lo) <= ln 0.99."""
    flo = f_of(lo, r, N, xfun)
    if flo is None or flo <= ln_alpha:
        return None
    a, b = lo, 1 - mpf(10) ** -40
    for _ in range(steps):
        m = (a + b) / 2
        fm = f_of(m, r, N, xfun)
        if fm is not None and fm > ln_alpha:
            a = m
        else:
            b = m
    return (a + b) / 2

def steps_4_to_6(C, N, r, k, z, xfun):
    pg = mpf(C) / N
    if C == 0:
        pgp = 1 - mpf("0.01") ** (mpf(1) / N)
    else:
        pgp = min(mpf(1), pg + z * sqrt(pg * (1 - pg) / (N - 1)))
    lo = max(pgp, mpf(1) / k)
    pl = p_local(r, N, lo, xfun, log(mpf("0.99"))) if lo < 1 else None
    pmax = max(lo, pl) if pl is not None else lo
    return pg, pgp, pl, -log(pmax) / log(2)

def main():
    print("# lz78y-probe.py  (mpmath available: %s)" % HAVE_MP)
    if not HAVE_MP:
        print("mpmath missing: probes B and C skipped; probe A runs on integers only")

    # ------------------------------------------------------------ Probe A
    print("\n## Probe A: worked example, SP 800-90B 6.3.10 (PDF p. 65)")
    S = [2, 1, 3, 2, 1, 3, 1, 3, 1, 2, 1, 3, 2]
    expected = [0, 0, 1, 1, 0, 1, 1, 0]
    for seq in (True, False):
        correct, size = lz78y_spec(S, B=4, sequential=seq)
        tag = "SEQUENTIAL (i then ii; new entry nets 1)" if seq else "EXCLUSIVE (i or ii; new entry stays 0)"
        print("reading %-45s correct=%s dict=%d  %s" % (tag, correct, size,
              "MATCHES example" if correct == expected else "DOES NOT MATCH example"))
    if HAVE_MP:
        correct, _ = lz78y_spec(S, B=4, sequential=True)
        C, N, r = sum(correct), len(correct), longest_run(correct) + 1
        for zname, z in (("2.576 (printed)", mpf("2.576")), ("exact 0.995 quantile", mpf("2.5758293035489008"))):
            pg, pgp, pl, H = steps_4_to_6(C, N, r, 3, z, lambda p, r: x_iter(p, r, 10))
            print("z=%-22s C=%d N=%d r=%d  P_global=%s  P_global'=%s  P_local=%s  H=%s" % (
                zname, C, N, r, mp.nstr(pg, 6), mp.nstr(pgp, 6),
                mp.nstr(pl, 6) if pl is not None else "n/a(<=lo)", mp.nstr(H, 6)))
        print("example states: P_global=0.5 P_global'=0.9868 P_local=0.1229 H=0.0191")
        # P_local in the example is below lo (=0.9868), so the example must have solved it unbracketed:
        pl_free = p_local(r, N, mpf(1) / 3, lambda p, r: x_iter(p, r, 10), log(mpf("0.99")))
        print("P_local solved on [1/3, 1) instead of [P_global', 1): %s" % (mp.nstr(pl_free, 6) if pl_free is not None else "none"))
        pl_free2 = p_local(r, N, mpf("1e-6"), lambda p, r: x_iter(p, r, 10), log(mpf("0.99")))
        print("P_local solved on [1e-6, 1): %s" % (mp.nstr(pl_free2, 6) if pl_free2 is not None else "none"))

    if not HAVE_MP:
        return

    # ------------------------------------------------------------ Probe B
    print("\n## Probe B: F08 -- x_10 (spec step 5) vs x iterated to convergence")
    print("P_local(x_10) - P_local(x_conv) > 0 means the converged form gives the LOWER P_local, i.e. the HIGHER entropy (permissive).")
    ln_alpha = log(mpf("0.99"))
    rows = [(2, 1, 1), (2, 2, 2), (3, 2, 2), (17, 2, 2), (100, 3, 2), (1000, 5, 2),
            (9983, 19, 2), (999983, 20, 2), (999983, 73, 256), (7999983, 583, 2), (999983, 534, 2)]
    print("| N | r | k | P_local(x10) | P_local(xconv) | dP | dH (bit, conv - x10) |")
    print("|---:|---:|---:|---|---|---:|---:|")
    for N, r, k in rows:
        lo = mpf(1) / k
        p10 = p_local(r, N, lo, lambda p, r: x_iter(p, r, 10), ln_alpha)
        pcv = p_local(r, N, lo, x_conv, ln_alpha)
        if p10 is None or pcv is None:
            print("| %d | %d | %d | %s | %s | - | - |" % (N, r, k, p10, pcv))
            continue
        dH = (-log(pcv) + log(p10)) / log(2)
        print("| %d | %d | %d | %s | %s | %s | %s |" % (N, r, k, mp.nstr(p10, 17), mp.nstr(pcv, 17),
              mp.nstr(p10 - pcv, 4), mp.nstr(dH, 4)))
    # how many iterations does convergence take at a compliant point?
    for (N, r) in ((999983, 20), (999983, 2), (2, 1)):
        p = p_local(r, N, mpf(1) / 2, x_conv, ln_alpha) or mpf("0.5")
        q = 1 - p; x = mpf(1); n = 0
        while True:
            xn = 1 + q * p ** r * x ** (r + 1); n += 1
            if abs(xn - x) <= mpf(2) ** -63 * xn or n > 5000:
                break
            x = xn
        print("N=%d r=%d p=%s: iterations to |dx| <= 2^-63 x: %d; contraction factor q(r+1)p^r x^r = %s" % (
            N, r, mp.nstr(p, 8), n, mp.nstr(q * (r + 1) * p ** r * x ** r, 4)))

    # ------------------------------------------------------------ Probe C
    print("\n## Probe C: monotonicity of f(p) in p on a grid (x converged), per (r, N)")
    print("A violation would mean f(lo) <= ln 0.99 does NOT imply the root is <= lo.")
    viol = 0; pts = 0
    for N in (2, 3, 10, 100, 1000, 10**6, 8 * 10**6):
        for r in (1, 2, 3, 5, 10, 20, 100, 600):
            if r > N:
                continue
            hi = mpf(r) / (r + 1)
            prev = None
            grid = [mpf(i) / 2000 for i in range(1, 2000)]
            grid = [g for g in grid if g < hi]
            for p in grid:
                fv = f_of(p, r, N, x_conv)
                pts += 1
                if fv is None:
                    continue
                if prev is not None and fv > prev + mpf(10) ** -45:
                    viol += 1
                    if viol <= 10:
                        print("NON-MONOTONE at N=%d r=%d p=%s: f=%s > prev %s" % (N, r, mp.nstr(p, 6), mp.nstr(fv, 12), mp.nstr(prev, 12)))
                prev = fv
    print("grid points: %d; monotonicity violations: %d" % (pts, viol))
    print("(rule 6: this is evidence about the (r, N, p) rows sampled, not a proof.)")

if __name__ == "__main__":
    main()
