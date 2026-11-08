#!/usr/bin/env python3
"""Emulate cpp/shared/utils.h predictionEstimate -> prediction_estimate_function in
IEEE double, exactly as the C code orders the operations, to ask ONE question:

  Can the guard call prediction_estimate_function(curMax, max_run_len+1, N) at
  utils.h:1151 trip assert(p*x <= 1.0L) (utils.h:1105) or assert(x >= xlast)
  (utils.h:1103) for (C, N, r) triples a near-perfect predictor can produce?

On this host (Darwin arm64, Apple clang) long double IS double, powl is pow and
logl is log, so Python's float/math.pow/math.log reproduce the C arithmetic.
On x86-64 (80-bit long double) the emulation is NOT faithful; stated as such.

The triples swept are the ones "period-2 data with isolated same-phase bit flips"
produces in the binary LZ78Y predictor: C ~ N - (misses), max run ~ spacing.
"""
import math, sys

ZALPHA = 2.5758293035489008
DBL_EPSILON = 2.220446049250313e-16
LOG099 = math.log(0.99)

def p_global_prime(C, N):
    p = float(C) / float(N)
    if p > 0:
        return min(1.0, p + ZALPHA * math.sqrt((p * (1.0 - p)) / (float(N) - 1.0)))
    return 1.0 - math.pow(0.01, 1.0 / float(N))

def pef_emulated(p, r, N):
    """Returns (status, value, iterations). status in {'ok','ASSERT_px','ASSERT_mono','domain'}"""
    assert 0.0 < p < 1.0
    q = 1.0 - p
    x = 1.0
    xlast = 0.0
    i = 0
    while i <= 65 and (x - xlast) > DBL_EPSILON * x:
        xlast = x
        x = 1.0 + q * math.pow(p, r) * math.pow(x, r + 1.0)
        if not (x >= xlast):
            return ('ASSERT_mono', None, i)
        if not (p * x <= 1.0):
            return ('ASSERT_px', p * x, i)
        i += 1
    a = 1.0 - p * x
    b = (r + 1.0 - r * x) * q
    if a <= 0.0 or b <= 0.0:
        return ('domain(log<=0)', (a, b), i)
    return ('ok', math.log(a) - math.log(b) - (N + 1.0) * math.log(x), i)

def guard(C, N, r, k):
    curMax = max(1.0 / k, p_global_prime(C, N))
    if not (curMax < 1.0):
        return ('skip(curMax>=1)', curMax, None)
    st, val, it = pef_emulated(curMax, r, N)
    return (st, curMax, (val, it))

def main():
    print("# lz78y-assert-emulation.py -- double-precision emulation of utils.h:1087-1108 at the guard call utils.h:1151")
    print("# faithful ONLY where long double == double (this host: Darwin arm64)")
    total = 0; aborts = 0; domain = 0
    examples = []
    # Scenario family: L bits of period-2 data, a same-phase flip every P bits, m misses per flip plus m0 warm-up misses.
    for L in (1000, 5000, 10000, 20000, 1000000, 8000000):
        N = L - 17
        for P in (50, 100, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 10000, 20000, 50000, 100000, 200000):
            if P >= N // 2:
                continue
            glitches = N // P
            for m0 in (1, 2, 3):
                for m in (1, 2):
                    misses = m0 + m + (glitches - 1) * 1   # first glitch costs m, later ones ~1 (stored context)
                    C = N - misses
                    for run_adj in (0, -1, -2, 1):
                        r = (P - 1) + run_adj            # max run ~ P-1 corrects between flips; r = run+1
                        if r < 1 or C <= 0 or C > N:
                            continue
                        total += 1
                        st, cm, extra = guard(C, N, r, 2)
                        if st.startswith('ASSERT'):
                            aborts += 1
                            if len(examples) < 40:
                                examples.append((L, N, P, C, r, cm, st, extra))
                        elif st.startswith('domain'):
                            domain += 1
    print("triples tried: %d; emulated assert aborts: %d; log-domain (a<=0 or b<=0, would give -inf/NaN): %d" % (total, aborts, domain))
    print("| L | N | P | C | r | curMax=P_global' | status | p*x or f, iterations |")
    print("|---:|---:|---:|---:|---:|---|---|---|")
    for L, N, P, C, r, cm, st, extra in examples:
        print("| %d | %d | %d | %d | %d | %.17g | %s | %r |" % (L, N, P, C, r, cm, st, extra))
    # Fine sweep at one tiny-probe size, to pick concrete (P) values for the binary run:
    print("\n## Fine sweep at L=20000 (N=19983), k=2: which (C, r) abort?  (P spacing 300..2000)")
    N = 19983
    hits = []
    for P in range(300, 2001, 1):
        glitches = N // P
        for misses in range(glitches, glitches + 6):
            C = N - misses
            for r in (P - 2, P - 1, P, P + 1):
                st, cm, extra = guard(C, N, r, 2)
                if st.startswith('ASSERT'):
                    hits.append((P, C, r, cm, st, extra))
    print("aborting (P, C, r) combos: %d" % len(hits))
    for h in hits[:60]:
        print("P=%d C=%d r=%d curMax=%.17g %s %r" % h)
    # And how the region looks for a genuinely random-ish predictor (control: must be 'ok')
    print("\n## Control: ordinary (C, r) for N=999983 must be 'ok'")
    for C, r in ((499990, 20), (979970, 534), (799263, 73), (4998, 19)):
        Nn = 999983 if C > 10000 else 9983
        print("N=%d C=%d r=%d -> %r" % (Nn, C, r, guard(C, Nn, r, 2)))

if __name__ == '__main__':
    main()
