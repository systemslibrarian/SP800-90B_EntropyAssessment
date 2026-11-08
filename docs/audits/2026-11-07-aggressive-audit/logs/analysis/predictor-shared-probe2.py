#!/usr/bin/env python3
"""
predictor-shared-probe2.py -- dense sweep of the P_local bisection error (the C22a
mechanism) in the OVERSTATING direction, at the operating point and at the N where
probe 1 saw the C22a formula exceeded.

For each (N, r): p_code = calc_p_local transliteration (binary64, as on Darwin arm64);
p_exact = root of the exact Feller equation (x converged) in 60-digit decimal, bisected
inside a narrow bracket around p_code.  dH = -log2(p_code) + log2(p_exact): POSITIVE means
the tool reports MORE entropy than the exact solution of the spec's equation.

Compared against the floor's C22a term 8.08e-15 * (N+1)  (oracles/entropy_floor.py).

Also prints the explicit degenerate-state checks the task asked for: C == 0 (r == 1),
C == N (r == N+1), max_run_len == N-1 (r == N), N == 1, N == 2.
"""
import math, sys, importlib.util
from decimal import Decimal, getcontext
getcontext().prec = 60

spec = importlib.util.spec_from_file_location('p1', sys.argv[2])
p1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p1)

C22A_CONST = Decimal('8.08e-15')
LOG2 = Decimal(2).ln()

def F_exact_conv(P, r, N):
    P = Decimal(P); q = 1 - P
    x = Decimal(1)
    for _ in range(2000):
        xn = 1 + q * (P ** r) * (x ** (r + 1))
        if abs(xn - x) < Decimal(10) ** -56:
            x = xn; break
        x = xn
    a = 1 - P * x; b = (r + 1 - r * x) * q
    if a <= 0 or b <= 0: return Decimal('-Infinity')
    return a.ln() - b.ln() - (N + 1) * x.ln()

TARGET = Decimal('0.99').ln()

def exact_root_near(pc, r, N):
    # bracket: F is decreasing in P.  widen until bracketed.
    w = Decimal('1e-6')
    lo = Decimal(repr(pc)) - w; hi = Decimal(repr(pc)) + w
    if lo <= 0: lo = Decimal('1e-30')
    if hi >= 1: hi = 1 - Decimal('1e-30')
    while F_exact_conv(lo, r, N) < TARGET:
        lo = lo / 2
    while F_exact_conv(hi, r, N) > TARGET:
        hi = (hi + 1) / 2
    for _ in range(130):
        mid = (lo + hi) / 2
        if F_exact_conv(mid, r, N) > TARGET: lo = mid
        else: hi = mid
        if hi - lo < Decimal(10) ** -36: break
    return (lo + hi) / 2

def main(out):
    def emit(s=''):
        print(s); out.write(s + '\n')
    emit('# predictor-shared-probe2.py -- dense P_local bisection-error sweep, overstating direction vs C22a')
    emit('# dH > 0  ==>  tool reports MORE entropy than the exact root of the spec equation')
    emit()
    plans = [
        (999937, list(range(2, 61)) + list(range(65, 301, 5)) + [400, 500, 700, 1000, 1500, 2000, 3000, 5000, 10000]),
        (999999, list(range(2, 61)) + list(range(65, 301, 5))),
        (4033,   list(range(2, 61)) + list(range(65, 301, 5)) + [400, 600, 1000]),
        (7999937, list(range(2, 41)) + list(range(45, 201, 5))),
    ]
    grand = []
    for N, rs in plans:
        c22a = C22A_CONST * (N + 1)
        worst_over = (Decimal(0), None); worst_under = (Decimal(0), None); n_over = 0; n_rows = 0
        exceed_over = []; exceed_any = []
        for r in rs:
            if r >= N: continue
            pc, path, _ = p1.calc_p_local(r - 1, N, 1e-12)
            pe = exact_root_near(pc, r, N)
            dH = (-Decimal(repr(pc)).ln() + pe.ln()) / LOG2
            n_rows += 1
            if dH > 0:
                n_over += 1
                if dH > worst_over[0]: worst_over = (dH, r)
                if dH > c22a: exceed_over.append((r, float(dH), path))
            else:
                if -dH > worst_under[0]: worst_under = (-dH, r)
            if abs(dH) > c22a: exceed_any.append((r, float(dH), path))
        emit('N=%d  rows=%d  rows_overstating=%d  C22a(N)=%.3e bit' % (N, n_rows, n_over, c22a))
        emit('   worst OVERSTATING dH = %.3e bit at r=%s   (ratio to C22a: %.2f)' % (worst_over[0], worst_over[1], (worst_over[0] / c22a) if c22a else 0))
        emit('   worst understating dH = %.3e bit at r=%s   (ratio to C22a: %.2f)' % (worst_under[0], worst_under[1], (worst_under[0] / c22a) if c22a else 0))
        emit('   rows where OVERSTATING dH > C22a: %d  %s' % (len(exceed_over), exceed_over[:10]))
        emit('   rows where |dH| > C22a (either direction): %d  %s' % (len(exceed_any), exceed_any[:10]))
        grand.append((N, float(worst_over[0]), worst_over[1], float(c22a), len(exceed_over), len(exceed_any)))
        emit()
    emit('## summary: N, worst overstating dH, at r, C22a(N), #over>C22a, #|dH|>C22a')
    for g in grand: emit('   %s' % (g,))
    emit()
    emit('## degenerate states (transliteration of predictionEstimate): C==0, C==N, r==N, N==1, N==2')
    for (C, N, m, k) in [(0, 1000000, 0, 2), (0, 1000000, 0, 256), (0, 2, 0, 2), (1000000, 1000000, 1000000, 2), (999999, 1000000, 999999, 2),
                         (999998, 1000000, 999998, 256), (0, 1, 0, 3), (1, 1, 1, 3), (1, 2, 1, 3), (2, 2, 2, 3), (0, 2, 0, 3), (1, 2, 1, 2),
                         (999937 - 7, 999937, 999937 - 7, 2), (999937 - 6, 999937, 999937 - 6, 2), (999937 - 5, 999937, 999937 - 5, 2)]:
        tr = {}
        try:
            res = p1.predictionEstimate(C, N, m, k, track=tr)
            emit('   C=%d N=%d max_run=%d k=%d -> Pglobal\'=%.17g P_local=%s H=%.17g exit=%s assert1105=%s' %
                 (C, N, m, k, res['P_global_prime'], ('%.17g' % res['P_local']) if res['P_local'] > 0 else 'n/a', res['min_entropy'], res['exit'], tr.get('assert_would_fire', False)))
        except Exception as e:
            emit('   C=%d N=%d max_run=%d k=%d -> EXCEPTION %r' % (C, N, m, k, e))
    emit()
    emit('# end of probe2')

if __name__ == '__main__':
    with open(sys.argv[1], 'w') as out:
        main(out)
