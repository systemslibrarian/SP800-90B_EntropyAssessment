#!/usr/bin/env python3
"""
predictor-shared-probe.py -- ANALYSIS-PHASE PROBE for the shared prediction-estimate
machinery in cpp/shared/utils.h (prediction_estimate_function, calc_p_local,
predictionEstimate).

THIS IS A TRANSLITERATION OF THE C++, NOT AN INDEPENDENT REFERENCE. It exists only to
answer numeric questions about the C++ itself that reading cannot settle:

  Q1  Does the code's iterate-to-convergence x (<= 66 steps) differ from the spec's
      fixed x = x_10 (SP 800-90B 6.3.7 step 6, PDF p.58) by enough to move P_local?
      (tracker F08: "effect < 1e-10. UNVERIFIED")
  Q2  Is the returned P_local on the conservative side of the exact root (hbound),
      i.e. never BELOW the exact root by more than rounding?  (A P_local below the
      root OVERSTATES entropy.)
  Q3  Does the transliteration reproduce the standard's four worked examples and
      spot rows of Appendix G.2 Table 3 (PDF p.84)?  This validates the transcription.
  Q4  Can assert(p*x <= 1.0L) at utils.h:1105 fire on this host's float format when
      p > r/(r+1) (the regime where the recurrence converges to x = 1/p; tracker F24)?
  Q5  For every reachable (C, max_run_len, N) at small N, does the bisection ever
      probe a p > r/(r+1)?  (If it did, F would be -inf/NaN or the assert could fire.)

Host note: on Apple arm64, C `long double` IS binary64, so Python floats reproduce
the host's long-double arithmetic bit-for-bit except for libm differences in
powl/logl.  On x86-64 (80-bit x87 long double) the results would differ in the last
digits; this probe speaks for Darwin arm64 only.
"""
import math, sys, json
from decimal import Decimal, getcontext
getcontext().prec = 60
def mpf(v):
    return Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
def mlog(v, base=None):
    v = mpf(v) if not isinstance(v, Decimal) else v
    if v <= 0: return Decimal('-Infinity')
    r = v.ln()
    return r / Decimal(base).ln() if base else r
def mpow(b, e):
    b = mpf(b) if not isinstance(b, Decimal) else b
    return b ** (Decimal(e) if not isinstance(e, Decimal) else e)
class _mp:
    @staticmethod
    def nstr(v, n): return format(v, '.%dg' % n)
mp = _mp()

LDBL_EPSILON = 2.0 ** -52           # == DBL_EPSILON on Apple arm64 (long double == double)
DBL_EPSILON = 2.0 ** -52
DBL_MIN = 2.2250738585072014e-308
ZALPHA = 2.5758293035489008
Z_TEXT = 2.576
ITERMAX = 1076
LOG_ALPHA = math.log(0.99)

# ---------------------------------------------------------------------------------
# Transliteration of utils.h:1087-1109 (prediction_estimate_function)
# ---------------------------------------------------------------------------------
def pef(p, r, N, track=None):
    assert p > 0.0
    assert p < 1.0
    q = 1.0 - p
    x = 1.0
    xlast = 0.0
    i = 0
    while (i <= 65) and ((x - xlast) > (LDBL_EPSILON * x)):
        xlast = x
        x = 1.0 + q * math.pow(p, r) * math.pow(x, r + 1.0)
        assert x >= xlast, (p, r, N, x, xlast)
        if track is not None:
            track['px_max'] = max(track.get('px_max', 0.0), p * x)
            track['iters'] = i + 1
        # utils.h:1105 -- we do NOT assert here; we record whether it WOULD fire
        if p * x > 1.0:
            if track is not None:
                track['assert_would_fire'] = True
            else:
                raise AssertionError("p*x > 1.0 at p=%r r=%r N=%r x=%r" % (p, r, N, x))
        i += 1
    a = 1.0 - p * x
    b = (r + 1.0 - r * x) * q
    # logl of 0 -> -inf, of negative -> nan; mirror C
    def logl(v):
        if v > 0: return math.log(v)
        if v == 0: return -math.inf
        return math.nan
    return logl(a) - logl(b) - (N + 1.0) * math.log(x)

# ---------------------------------------------------------------------------------
# Transliteration of utils.h:115-198 (relEpsilonEqual), simplified to the branches
# reachable with finite inputs
# ---------------------------------------------------------------------------------
def relEpsilonEqual(A, B, maxAbs, maxRel, maxULP):
    if math.isnan(A) or math.isnan(B): return False
    if A == B: return True
    if math.isinf(A) or math.isinf(B): return False
    absA, absB = abs(A), abs(B)
    if absA > absB:
        A, B = B, A; absA, absB = absB, absA
    diff = abs(B - A)
    if (absA < DBL_MIN) or (diff < DBL_MIN) or math.isinf(diff) or (absB * maxRel < DBL_MIN):
        return diff <= maxAbs
    if diff <= absB * maxRel: return True
    if math.copysign(1, A) != math.copysign(1, B): return False
    import struct
    Aint = struct.unpack('<Q', struct.pack('<d', absA))[0]
    Bint = struct.unpack('<Q', struct.pack('<d', absB))[0]
    return (Bint - Aint) <= maxULP

def inclosed(x, a, b):
    return (x >= b and x <= a) if a > b else (x >= a and x <= b)
def inopen(x, a, b):
    return (x > b and x < a) if a > b else (x > a and x < b)

# ---------------------------------------------------------------------------------
# Transliteration of utils.h:1111-1198 (calc_p_local); returns (p, exit_path, max_probe)
# ---------------------------------------------------------------------------------
def calc_p_local(max_run_len, N, ldomain, track=None):
    log_alpha = LOG_ALPHA
    hdomain = 1.0
    lbound, hbound = ldomain, hdomain
    lvalue, hvalue = math.inf, -math.inf
    p = (lbound + hbound) / 2.0
    max_probe = p
    pVal = pef(p, max_run_len + 1, N, track)
    path = 'ITERMAX'
    for j in range(ITERMAX):
        if relEpsilonEqual(pVal, log_alpha, DBL_MIN, DBL_EPSILON, 4):
            path = 'relEpsilonEqual'; break
        if log_alpha < pVal:
            lbound = p; lvalue = pVal
        else:
            hbound = p; hvalue = pVal
        if lbound >= hbound:
            p = min(max(lbound, hbound), hdomain); path = 'lbound>=hbound'; break
        if not (inclosed(lbound, ldomain, hdomain) and inclosed(hbound, ldomain, hdomain)):
            p = hdomain; path = 'domain-invariant'; break
        if not inclosed(log_alpha, lvalue, hvalue):
            p = hdomain; path = 'target-not-bracketed'; break
        lastP = p
        p = (lbound + hbound) / 2.0
        if not inopen(p, lbound, hbound):
            p = hbound; path = 'midpoint-collapse'; break
        if lastP == p:
            p = hbound; path = 'cycle'; break
        max_probe = max(max_probe, p)
        pVal = pef(p, max_run_len + 1, N, track)
        if not inclosed(pVal, lvalue, hvalue):
            p = hbound; path = 'non-monotone'; break
    return p, path, max_probe

# ---------------------------------------------------------------------------------
# Transliteration of utils.h:1200-1256 (predictionEstimate)
# ---------------------------------------------------------------------------------
def predictionEstimate(C, N, max_run_len, k, z=ZALPHA, track=None):
    curMax = 1.0 / k
    p_global = C / N
    if p_global > 0:
        v = p_global + z * math.sqrt((p_global * (1.0 - p_global)) / (N - 1.0))
        # std::min(1.0, v): returns v if v < 1.0 else 1.0 ; NaN -> 1.0
        p_globalPrime = v if (v < 1.0) else 1.0
    else:
        p_globalPrime = 1.0 - math.pow(0.01, 1.0 / N)
    curMax = max(curMax, p_globalPrime)
    p_local = -1.0
    path = 'not-computed'
    max_probe = None
    if (curMax < 1.0) and (pef(curMax, max_run_len + 1, N, track) > LOG_ALPHA):
        p_local, path, max_probe = calc_p_local(max_run_len, N, curMax, track)
        curMax = max(curMax, p_local)
    return dict(C=C, N=N, r=max_run_len + 1, P_global=p_global, P_global_prime=p_globalPrime,
                P_local=p_local, min_entropy=-math.log2(curMax), exit=path, max_probe=max_probe)

# ---------------------------------------------------------------------------------
# SPEC-LITERAL high-precision references (mpmath), from the text of 6.3.7 step 6:
#   0.99 = (1 - P x)/((r+1-r x) q) * 1/x^(N+1),  x = x_10,  x_j = 1 + q P^r x_{j-1}^(r+1)
# Two variants: x = x_10 (literal), and x = x_inf (converged), both in 60-digit arithmetic,
# root found by bisection on P in (0,1) to 1e-40.
# ---------------------------------------------------------------------------------
def F_exact(P, r, N, iters):
    P = mpf(P); q = 1 - P
    x = mpf(1)
    if iters is None:
        for _ in range(400):
            xn = 1 + q * mpow(P, r) * mpow(x, r + 1)
            if abs(xn - x) < Decimal(10) ** -55: x = xn; break
            x = xn
    else:
        for _ in range(iters):
            x = 1 + q * mpow(P, r) * mpow(x, r + 1)
    a = 1 - P * x
    b = (r + 1 - r * x) * q
    if a <= 0 or b <= 0:
        return Decimal('-Infinity')
    return mlog(a) - mlog(b) - (N + 1) * mlog(x)

def plocal_exact(r, N, iters, lo=mpf('1e-30'), hi=mpf(1) - mpf('1e-30')):
    target = mlog(mpf('0.99'))
    # F decreasing in P; find P with F(P) = target
    flo = F_exact(lo, r, N, iters)
    if flo < target:
        return mpf(0)
    for _ in range(200):
        mid = (lo + hi) / 2
        if F_exact(mid, r, N, iters) > target: lo = mid
        else: hi = mid
        if hi - lo < Decimal(10) ** -40: break
    return (lo + hi) / 2

def main(out):
    def emit(s=''):
        print(s); out.write(s + '\n')

    emit('# predictor-shared-probe.py -- transliteration probe of cpp/shared/utils.h prediction machinery')
    emit('# host: Darwin arm64 assumed (long double == double); python %s' % sys.version.split()[0])
    emit('# This probe runs NO tool binary and reads NO input file.')
    emit()

    # ---------------- Q3: worked examples and Table 3 ----------------
    emit('## Q3  Worked examples (spec text uses 2.576; code uses ZALPHA) ')
    examples = [
        ('6.3.7 MultiMCW example p.58-59', dict(C=3, N=9, max_run_len=1, k=3), dict(Pgp=0.7627, Pl=0.036, H=0.3908)),
        ('6.3.8 Lag example p.60',         dict(C=2, N=9, max_run_len=2, k=3), dict(Pgp=0.6008, Pl=0.1167, H=0.735)),
        ('6.3.9 MultiMMC example p.63',    dict(C=3, N=7, max_run_len=2, k=3), dict(Pgp=0.9490, Pl=0.1307, H=0.0755)),
        ('6.3.10 LZ78Y example p.65',      dict(C=4, N=8, max_run_len=2, k=3), dict(Pgp=0.9868, Pl=0.1229, H=0.0191)),
    ]
    for name, args, want in examples:
        for z, zname in ((Z_TEXT, '2.576'), (ZALPHA, 'ZALPHA')):
            res = predictionEstimate(args['C'], args['N'], args['max_run_len'], args['k'], z=z)
            # spec computes P_local unconditionally; the code skips it when it cannot bind.
            pl_spec10 = float(plocal_exact(args['max_run_len'] + 1, args['N'], 10))
            pl_specinf = float(plocal_exact(args['max_run_len'] + 1, args['N'], None))
            emit('%-32s z=%-6s Pglobal\'=%.6f (want %.4f)  P_local(code)=%s  P_local(spec x10)=%.6f  P_local(spec xinf)=%.6f (want %.4f)  H=%.6f (want %.4f) exit=%s'
                 % (name, zname, res['P_global_prime'], want['Pgp'],
                    ('%.6f' % res['P_local']) if res['P_local'] > 0 else 'skipped', pl_spec10, pl_specinf, want['Pl'],
                    res['min_entropy'], want['H'], res['exit']))
    emit()
    emit('## Q3b Appendix G.2 Table 3 spot rows (L = 1 000 000).  Columns: r, table, code N=L, code N=L-1, spec-x10 N=L')
    table3 = {1: 0.0000, 2: 0.0001, 3: 0.0022, 4: 0.0100, 5: 0.0253, 10: 0.1614, 20: 0.4088, 35: 0.6068,
              36: 0.6157, 49: 0.7040, 55: 0.7092, 60: 0.7328, 100: 0.8398, 1000: 0.9860, 10000: 0.9988}
    for r, tv in sorted(table3.items()):
        m = r - 1
        a, _, _ = calc_p_local(m, 1_000_000, 1e-12) if r > 1 else (0.0, '', 0)
        b, _, _ = calc_p_local(m, 999_999, 1e-12) if r > 1 else (0.0, '', 0)
        s = float(plocal_exact(r, 1_000_000, 10)) if r > 1 else 0.0
        emit('r=%5d  table=%.4f  code(N=L)=%.6f  code(N=L-1)=%.6f  spec-x10(N=L)=%.6f' % (r, tv, a, b, s))
    emit()

    # ---------------- Q1 + Q2: x10 vs converged; code vs exact root ----------------
    emit('## Q1/Q2  P_local: code (double, converged x) vs exact root with x_inf vs exact root with x_10')
    emit('## columns: N r  P_code  P_exact_xinf  P_exact_x10  (code-xinf)  (x10-xinf)  dH_code_vs_x10_bits  exit')
    worst = dict(dP_code_vs_xinf=0.0, dP_x10_vs_xinf=0.0, dH_code_vs_x10=0.0, below_root=0, rows=0)
    for N in (999_937, 999_999, 7_999_937, 4033, 1000, 100, 20):
        rs = [2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
        for r in rs:
            if r >= N: continue
            m = r - 1
            pc, path, _ = calc_p_local(m, N, 1e-12)
            pi = plocal_exact(r, N, None)
            p10 = plocal_exact(r, N, 10)
            d1 = pc - float(pi); d2 = float(p10 - pi)
            dH = float(-mlog(mpf(pc), 2) + mlog(p10, 2)) if pc > 0 and p10 > 0 else float('nan')
            worst['rows'] += 1
            worst['dP_code_vs_xinf'] = max(worst['dP_code_vs_xinf'], abs(d1))
            worst['dP_x10_vs_xinf'] = max(worst['dP_x10_vs_xinf'], abs(d2))
            if not math.isnan(dH): worst['dH_code_vs_x10'] = max(worst['dH_code_vs_x10'], abs(dH))
            if mpf(pc) < pi - mpf(pc) * mpf(DBL_EPSILON) * 2:
                worst['below_root'] += 1
            emit('%8d %4d  %.17g  %s  %s  %+.3e  %+.3e  %+.3e  %s'
                 % (N, r, pc, mp.nstr(pi, 20), mp.nstr(p10, 20), d1, d2, dH, path))
    emit('## worst over %d rows: |P_code - P_exact_xinf| = %.3e ; |P_x10 - P_xinf| = %.3e ; |dH code vs spec-x10| = %.3e bit ; rows with P_code below exact root by > 2 ulp: %d'
         % (worst['rows'], worst['dP_code_vs_xinf'], worst['dP_x10_vs_xinf'], worst['dH_code_vs_x10'], worst['below_root']))
    emit()

    # ---------------- Q4: assert(p*x <= 1) in the p > r/(r+1) regime ----------------
    emit('## Q4  utils.h:1105 assert(p*x <= 1.0L): evaluate the recurrence in binary64 for p above r/(r+1)')
    fires = 0; total = 0; examples_fired = []
    for r in list(range(1, 65)) + [100, 1000, 37700]:
        thr = r / (r + 1.0)
        # dense grid just above the threshold up to 1 - 1e-9, plus the dangerous "fast convergence" region
        ps = [thr + (1 - thr) * t for t in (1e-6, 1e-4, 1e-3, 0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.99, 0.999)]
        for p in ps:
            if not (0 < p < 1): continue
            tr = {}
            try:
                f = pef(p, r, 1_000_000, tr)
            except AssertionError as e:
                fires += 1; examples_fired.append((r, p, 'x>=xlast assert')); total += 1; continue
            total += 1
            if tr.get('assert_would_fire'):
                fires += 1
                if len(examples_fired) < 20: examples_fired.append((r, p, tr['px_max'], f))
    emit('evaluations=%d   assert(p*x<=1) WOULD FIRE in %d of them on this float format' % (total, fires))
    for e in examples_fired[:20]:
        emit('   fired: %s' % (e,))
    # also report the three observable F outcomes at p just above threshold
    for r in (1, 2, 5, 20):
        p = r / (r + 1.0) + 0.3 * (1 - r / (r + 1.0))
        tr = {}
        f = pef(p, r, 1_000_000, tr)
        emit('   r=%d p=%.6f -> F=%s  iters=%d  p*x_max=%.17g  guard(F>log0.99)=%s' % (r, p, f, tr.get('iters', 0), tr.get('px_max', 0), f > LOG_ALPHA))
    emit()

    # ---------------- Q5: reachable states at small N: does any probe exceed r/(r+1)? ----------------
    emit('## Q5  exhaustive (C, max_run_len, N) for N in 2..80, k in {2,3,256}: probes vs r/(r+1); P_local >= curMax; exit paths')
    counts = {}
    violations = []
    computed = 0; states = 0
    for N in range(2, 81):
        for C in range(0, N + 1):
            for m in range(0, C + 1):
                if C > 0 and m == 0:  # a correct prediction implies a run of at least 1
                    continue
                for k in (2, 3, 256):
                    states += 1
                    tr = {}
                    res = predictionEstimate(C, N, m, k, track=tr)
                    counts[res['exit']] = counts.get(res['exit'], 0) + 1
                    if res['P_local'] > 0:
                        computed += 1
                        r = m + 1
                        if res['max_probe'] is not None and res['max_probe'] > r / (r + 1.0):
                            violations.append(('probe>r/(r+1)', N, C, m, k, res['max_probe']))
                        if res['P_local'] < max(1.0 / k, res['P_global_prime']):
                            violations.append(('P_local<curMax', N, C, m, k, res['P_local']))
                    if tr.get('assert_would_fire'):
                        violations.append(('assert1105', N, C, m, k))
                    if math.isnan(res['min_entropy']) or res['min_entropy'] < 0:
                        violations.append(('bad-entropy', N, C, m, k, res['min_entropy']))
    emit('states=%d  P_local computed in %d  exit-path counts=%s' % (states, computed, json.dumps(counts, sort_keys=True)))
    emit('violations=%d' % len(violations))
    for v in violations[:30]:
        emit('   %s' % (v,))
    emit()
    emit('# end of probe')

if __name__ == '__main__':
    outpath = sys.argv[1]
    with open(outpath, 'w') as out:
        main(out)
