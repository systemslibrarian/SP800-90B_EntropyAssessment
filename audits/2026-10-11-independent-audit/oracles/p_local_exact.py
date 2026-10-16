#!/usr/bin/env python3
"""OC-22 oracle and driver: C22's bound.

Independent high-precision evaluation of SP 800-90B section 6.3.7 steps 7-8
(P_local) written from the standard's formula, NOT from the tool's code:

    x  = the smallest positive root of  1 - x + q p^r x^(r+1) = 0,  q = 1 - p
    f(p) = ln(1 - p x) - ln((r + 1 - r x) q) - (N + 1) ln x
    P_local = the p with f(p) = ln(0.99)

The tool's prediction_estimate_function / calc_p_local are called through
reproducers/c22_bound.cpp (production headers), and the two are compared.

Usage:  p_local_exact.py <path-to-c22_bound-binary>
"""
import subprocess, sys, math, random
from mpmath import mp, mpf, log, sqrt, findroot, inf, diff, floor

mp.dps = 50
LN099 = log(mpf("0.99"))
TWO_M52 = mpf(2) ** -52
Z_TOOL = mpf("2.5758293035489008")
Z_SPEC = mpf("2.576")
LN2 = log(2)

HARNESS = sys.argv[1]

def run(*args):
    return subprocess.run([HARNESS] + [str(a) for a in args], capture_output=True, text=True, check=True).stdout

# ---------- the standard's formula, at 50 digits ----------
def x_root(p, r):
    """Smallest positive root of h(x) = 1 - x + q p^r x^(r+1).  Newton from x=1
    converges monotonically to it when p < r/(r+1) (h convex, h(1)>0, h'(1)<0).
    For p >= r/(r+1) the smallest root is x = 1/p itself, where ln(1 - p x) = -inf."""
    p = mpf(p); q = 1 - p
    if p >= mpf(r) / (r + 1) * (1 - mpf(10) ** -20):
        return None
    c = q * p ** r
    x = mpf(1)
    for _ in range(2000):
        h = 1 - x + c * x ** (r + 1)
        hp = -1 + (r + 1) * c * x ** r
        step = h / hp
        x = x - step
        if abs(step) < mpf(10) ** (-(mp.dps - 4)) * x:
            break
    return x

def f_exact(p, r, N):
    p = mpf(p); q = 1 - p
    x = x_root(p, r)
    if x is None or 1 - p * x <= 0 or (r + 1 - r * x) <= 0:
        return -inf                 # at (or within rounding of) the boundary x = 1/p: ln(0) = -inf
    return log(1 - p * x) - log((r + 1 - r * x) * q) - (N + 1) * log(x)

def p_star(r, N, lo):
    """Root of f(p) = ln 0.99 on [lo, r/(r+1)).  Returns None when f(lo) <= ln 0.99
    (P_local then cannot affect the result, exactly the production guard)."""
    lo = mpf(lo)
    if r > N:                       # a run of r needs N >= r trials: no root exists
        return None
    if f_exact(lo, r, N) <= LN099:
        return None
    hi = mpf(r) / (r + 1)
    if f_exact(hi * (1 - mpf(10) ** -10), r, N) > LN099:
        return None                 # f stays above ln 0.99 up to the boundary: no root
    for _ in range(170):            # 2^-170: far below any double
        mid = (lo + hi) / 2
        if f_exact(mid, r, N) > LN099:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

# ---------- transcription check: Feller vs exact DP for small cases ----------
def p_norun_dp(p, r, N):
    """Exact P(no run of r successes in N trials) by transfer matrix."""
    p = float(p); q = 1 - p
    state = [1.0] + [0.0] * (r - 1)          # state[j] = prob current run length j
    for _ in range(N):
        new = [0.0] * r
        for j in range(r):
            new[0] += state[j] * q
            if j + 1 < r:
                new[j + 1] += state[j] * p
        state = new
    return sum(state)

print("# OC-22 oracle run.  mp.dps =", mp.dps)
print(run("info").strip())
print()
print("## Transcription check: exp(f) (Feller approximation, as the standard specifies) vs exact DP")
for (p, r, N) in [(0.5, 5, 100), (0.3, 3, 50), (0.9, 10, 200), (0.1, 2, 20)]:
    fe = math.exp(float(f_exact(p, r, N)))
    dp = p_norun_dp(p, r, N)
    print(f"p={p} r={r} N={N}: feller={fe:.10g} dp={dp:.10g} rel={abs(fe-dp)/dp:.2e}")
print()

# ---------- 1. eps_f: the tool's f vs the exact f NEAR THE ROOT, in units of (N+1)*2^-52 ----------
print("## 1. Evaluation error of the tool's prediction_estimate_function near the root, |f_tool - f_exact| / ((N+1) 2^-52)")
print("(near the root is where the bisection's final decisions are made; far from it only the SIGN of f - ln 0.99 matters, checked separately)")
random.seed(22)
worst = (0, None)
rows = []
signbad = 0; signpts = 0
for N in [2, 10, 100, 1000, 10**4, 10**5, 10**6, 7999937, 10**7, 10**8, 2**31 - 1, 2**40]:
    for r in [2, 3, 5, 10, 24, 64, 256]:
        ps_ = p_star(r, N, mpf(2) ** -30)
        if ps_ is None:
            continue
        for k in (3, 6, 9, 12):
            for sgn in (-1, 1):
                p = ps_ * (1 + sgn * mpf(10) ** -k)
                pd = float(p)
                out = run("pef", float.hex(pd), r, N).split()
                ft = mpf(float.fromhex(out[0]))
                fe = f_exact(mpf(pd), r, N)
                err = abs(ft - fe) / ((N + 1) * TWO_M52)
                rows.append((N, r, pd, float(err)))
                if err > worst[0]:
                    worst = (err, (N, r, pd, float(ft), float(fe)))
        for _ in range(4):   # far from the root: sign only
            pd = random.uniform(float(ps_) * 1.5, float(mpf(r) / (r + 1)) * 0.98)
            if not (float(ps_) < pd < 1):
                continue
            out = run("pef", float.hex(pd), r, N).split()
            ft = float.fromhex(out[0]); fe = f_exact(mpf(pd), r, N)
            signpts += 1
            if (ft > float(LN099)) != (fe > LN099):
                signbad += 1
print(f"near-root points: {len(rows)}; worst |err|/((N+1) 2^-52) = {float(worst[0]):.4g} at (N,r,p,f_tool,f_exact) = {worst[1]}")
byN = {}
for N, r, pd, e in rows:
    byN[N] = max(byN.get(N, 0), e)
print("| N | max |err| / ((N+1) 2^-52) | max |err| (absolute) |")
print("|---:|---:|---:|")
for N in sorted(byN):
    print(f"| {N} | {byN[N]:.3g} | {byN[N]*(N+1)*2**-52:.3g} |")
C_EPS = max(e for *_, e in rows)
print(f"\nc := max near-root ratio = {C_EPS:.4g}   (eps_f <= c (N+1) 2^-52 near the root, on this build)")
print(f"far-from-root sign check: {signbad} of {signpts} points have the tool on the wrong side of ln 0.99 (the 66-step recurrence cap, predictors-7, lives here; sign is what the bisection consumes)")
print()

# ---------- 2. P_local: tool vs exact root, inflation in bits ----------
print("## 2. calc_p_local vs the exact root: inflation = log2(p* / p_tool) bit (positive = permissive)")
print("| N | r | ldomain | p_tool | p* | inflation (bit) | predicted ceiling c(N+1)2^-52/(|f'| p* ln2) | ratio |")
print("|---:|---:|---|---|---|---:|---:|---:|")
sweep = []
Ns = [2, 3, 5, 10, 30, 100, 1000, 10**4, 10**5, 10**6, 7999937, 8 * 10**6, 10**7, 10**8, 10**9, 2**31 - 1, 2**40, 2**53]
rs = [2, 3, 4, 5, 6, 8, 10, 16, 24, 32, 64, 128, 256, 1024]
lds = [mpf(1) / 2, mpf(1) / 256, mpf(1) / 65536, mpf(2) ** -30]
for N in Ns:
    for r in rs:
        for ld in lds:
            ps_ = p_star(r, N, ld)
            if ps_ is None:
                continue
            out = run("cpl", r, N, float.hex(float(ld))).split()
            pt = mpf(float.fromhex(out[0]))
            infl = log(ps_ / pt) / LN2
            fp = diff(lambda t: f_exact(t, r, N), ps_)
            K = TWO_M52 / (abs(fp) * ps_ * LN2)          # bit of inflation per (N+1) per 2^-52 of f error
            ceil = C_EPS * (N + 1) * K
            sweep.append((N, r, float(ld), float(pt), float(ps_), float(infl), float(ceil), float(infl / ceil), float(K), float(abs(fp) * ps_)))
# print the per-N worst rows plus the global worst
best = {}
for row in sweep:
    N = row[0]
    if N not in best or row[5] > best[N][5]:
        best[N] = row
for N in Ns:
    if N in best:
        N_, r, ld, pt, ps_, infl, ceil, ratio, K, fpp = best[N]
        print(f"| {N_} | {r} | {ld:.3g} | {pt:.17g} | {ps_:.17g} | {infl:+.3e} | {ceil:.3e} | {ratio:+.2f} |")
gw = max(sweep, key=lambda t: t[5])
print(f"\nsweep points: {len(sweep)}; worst inflation {gw[5]:+.4e} bit at N={gw[0]} r={gw[1]} ldomain={gw[2]:.3g}")
print(f"worst ratio inflation/ceiling over the sweep: {max(t[7] for t in sweep):+.3f}  (must be <= 1 for the ceiling to hold)")
print(f"conservative (negative) worst: {min(t[5] for t in sweep):+.4e} bit (at N={min(sweep, key=lambda t: t[5])[0]}, r={min(sweep, key=lambda t: t[5])[1]})")
Kmax = max(sweep, key=lambda t: t[8])
print(f"min over sweep of |f'(p*)| p* = {min(t[9] for t in sweep):.4e} (at N={min(sweep, key=lambda t: t[9])[0]} r={min(sweep, key=lambda t: t[9])[1]}); model 0.01005 (r - p/q) at r=2, N->inf: {0.01005*2:.4e}")
print(f"K := sup over sweep of 2^-52/(|f'(p*)| p* ln2) = {Kmax[8]:.4e} bit per unit N per ULP-of-f, at N={Kmax[0]} r={Kmax[1]}")
ceff = max(sweep, key=lambda t: t[5] / ((t[0] + 1) * t[8]))
print(f"effective ULP multiplier realised: max inflation/((N+1) K_point) = {ceff[5] / ((ceff[0] + 1) * ceff[8]):.3f} at N={ceff[0]} r={ceff[1]}  (compare c = {C_EPS:.3f})")
print(f"=> P_local ceiling c K (N+1): at N = 8e6: {C_EPS * Kmax[8] * (8e6 + 1):.3e} bit;  at N = 1e6: {C_EPS * Kmax[8] * 1e6:.3e} bit;  realised worst at N=8e6: {max((t[5] for t in sweep if t[0] == 8000000), default=0):+.3e} bit")
print()

# ---------- 3. P_global' on the approach to N == 1 ----------
print("## 3. P_global' on the approach to N == 1: tool path vs the standard's formula (exact z) vs the literal 2.576")
print("H_tool from predictionEstimate (production); H_spec(z) = -log2(max(1/k, min(1, C/N + z sqrt(C/N (1-C/N)/(N-1)))))")
print("| N | C | k | H_tool | H_spec(z exact) | H_spec(2.576) | tool - exact | tool - literal |")
print("|---:|---:|---:|---|---|---|---:|---:|")
def h_spec(C, N, k, z):
    pg = mpf(C) / N
    if C == 0:
        pp = 1 - mpf("0.01") ** (mpf(1) / N)
    elif N == 1:
        return mpf(0)   # the standard's formula is undefined at N == 1; the tool reports -0
    else:
        pp = min(mpf(1), pg + z * sqrt(pg * (1 - pg) / (N - 1)))
    cm = max(mpf(1) / k, pp)
    return -log(cm) / LN2
worst_lit = (mpf(0), None)
for N in [1, 2, 3, 4, 5, 8, 16, 64, 1000, 10**6, 8 * 10**6]:
    Cs = sorted(set([0, 1, 2, N // 2, N - 1, N]))
    for C in Cs:
        if C < 0 or C > N:
            continue
        for k in (2, 256):
            out = run("pe", C, N, max(1, min(C, 3)) if C else 0, k)
            ht = mpf(float.fromhex(out.strip().split("\n")[-1].split()[1]))
            he = h_spec(C, N, k, Z_TOOL); hl = h_spec(C, N, k, Z_SPEC)
            if ht - hl > worst_lit[0]:
                worst_lit = (ht - hl, (N, C, k))
            if N <= 5 or C in (0, 1, N):
                print(f"| {N} | {C} | {k} | {float(ht):.17g} | {float(he):.17g} | {float(hl):.17g} | {float(ht-he):+.3e} | {float(ht-hl):+.3e} |")
print(f"\nworst (tool - literal 2.576) over the grid: {float(worst_lit[0]):+.4e} bit at (N,C,k)={worst_lit[1]}")
dz = Z_SPEC - Z_TOOL
print(f"closed-form ceiling dz/((1+z) ln2) with dz = {float(dz):.10e}: {float(dz / ((1 + Z_TOOL) * LN2)):.4e} bit")
print()

# ---------- 4. ZALPHA on every estimator that uses it, from the harvested run ----------
print("## 4. ZALPHA: instance on the real run (logs/c22/predictor-intermediates.log) and mechanism ceiling, per estimator")
def ub(ph, n, z):
    return min(mpf(1), ph + z * sqrt(ph * (1 - ph) / (n - 1)))
closed = [
    ("Bitstring MCV", mpf("0.5003495"), 8000000),
    ("Literal MCV", mpf("0.004078"), 1000000),
    ("Bitstring t-Tuple", mpf("0.5231065809785963027778"), 8000000),
    ("Bitstring LRS", mpf("0.4999987422034614104049"), 8000000),
    ("Literal t-Tuple", mpf("0.004078000000000000027645"), 1000000),
    ("Literal LRS", mpf("0.003906341994563816526209"), 1000000),
    ("Bitstring MultiMCW P_global'", mpf("0.49985143633006107"), 7999937),
    ("Literal MultiMCW P_global'", mpf("0.0038532427542935207"), 999937),
    ("Bitstring Lag P_global'", mpf("0.49991343748917971"), 7999999),
    ("Literal Lag P_global'", mpf("0.0038440038440038442"), 999999),
    ("Bitstring MultiMMC P_global'", mpf("0.5002658750664688"), 7999998),
    ("Literal MultiMMC P_global'", mpf("0.0039660079320158644"), 999998),
    ("Bitstring LZ78Y P_global'", mpf("0.50022368797533689"), 7999983),
    ("Literal LZ78Y P_global'", mpf("0.0039670674401464821"), 999983),
]
print("| estimator | p-hat | n | H(z tool) | H(2.576) | instance (bit) | ceiling dz/((1+z)ln2) |")
print("|---|---|---:|---|---|---:|---:|")
ceil_closed = dz / ((1 + Z_TOOL) * LN2)
for name, ph, n in closed:
    ht = -log(ub(ph, n, Z_TOOL)) / LN2; hl = -log(ub(ph, n, Z_SPEC)) / LN2
    print(f"| {name} | {float(ph):.10g} | {n} | {float(ht):.17g} | {float(hl):.17g} | {float(ht-hl):+.3e} | {float(ceil_closed):.3e} |")
print()
# collision (bitstring only): X' = Xbar - z s/sqrt(v); p = 0.5 + sqrt(1.25 - 0.5 X'); H = -log2 p; X' >= 2.5 -> H = 1
def h_col(xp):
    xp = max(mpf(2), xp)
    if xp >= mpf("2.5"):
        return mpf(1)
    return -log(mpf("0.5") + sqrt(mpf("1.25") - mpf("0.5") * xp)) / LN2
Xb, s, v = mpf("2.500372711807354"), mpf("0.49999993922253266"), 3199523
ht = h_col(Xb - Z_TOOL * s / sqrt(v)); hl = h_col(Xb - Z_SPEC * s / sqrt(v))
print(f"Bitstring Collision instance: X'(tool) = {float(Xb - Z_TOOL*s/sqrt(v)):.17g} (log prints 2.4996526920512507), H(tool) = {float(ht):.17g} (log prints 0.96246938066617937), H(2.576) = {float(hl):.17g}, instance {float(ht-hl):+.3e} bit")
# ceiling: s <= 0.5 for t in {2,3}; v >= n/3; maximise H(X'+D) - H(X') over X'
for n in (10**6, 8 * 10**6):
    D = dz * mpf("0.5") / sqrt(mpf(n) / 3)
    best_ = mpf(0)
    for i in range(1, 200001):
        xp = mpf("2.5") - D * i / 1000      # scan the approach to the cap at fine resolution
        g = h_col(xp + D) - h_col(xp)
        if g > best_:
            best_ = g
    print(f"Bitstring Collision ceiling at n={n}: dX' <= {float(D):.3e}; max over X' of H(X'+dX')-H(X') = {float(best_):.4e} bit; closed form (2/ln2) sqrt(dX'/2) = {float(2/LN2*sqrt(D/2)):.4e} bit")
print()
# compression (bitstring only), through the production com_exp and the production solve
nb, vv = 1333333, 1332333
Xb, sg = "5.2187167977557474", "1.014743672733301"
o1 = run("comp", Xb, sg, vv, nb, float(Z_TOOL)); o2 = run("comp", Xb, sg, vv, nb, float(Z_SPEC))
def parse_comp(o):
    d = dict(l.split()[0:1] + [l.split()[1:]] for l in o.strip().split("\n") if l)
    return float.fromhex(d["H"][0]), float.fromhex(d["p"][0]), float(d["Xprime"][0])
Ht, pt, xt = parse_comp(o1); Hl, pl, xl = parse_comp(o2)
print(f"Bitstring Compression instance: X'(tool)={xt:.17g} p={pt:.17g} H={Ht:.17g} (log: 0.02121927244589572 / 0.92641349982744703); H(2.576)={Hl:.17g}; instance {Ht-Hl:+.3e} bit")
# ceiling: dX' <= dz * sigma_max / sqrt(v), sigma_max = 0.5907 * log2(num_blocks)/2 (Popoviciu, values in [0, log2 nb]).
# com_exp(p) = G(p) + 63 G((1-p)/63) is STATIONARY at p = 1/64 (G'(1/64) cancels), so the sensitivity is quadratic near the
# cap, not linear: scan X' up to G(1/64) through the production solve (comp with sigma = 0 gives X' = X exactly).
def h_comp(xp, nb_):
    o = run("comp", repr(float(xp)), "0", 1, nb_, "0")
    return float.fromhex([l for l in o.strip().split("\n") if l.startswith("H ")][0].split()[1])
for n in (10**6, 8 * 10**6):
    nb_ = n // 6; v_ = nb_ - 1000
    smax = mpf("0.5907") * log(nb_) / LN2 / 2
    D = float(dz * smax / sqrt(v_))
    g0 = float.fromhex(run("compgrid", nb_, 1).strip().split("\n")[0].split()[2])   # G(1/64) for this num_blocks
    best_ = (0, None)
    for i in range(0, 801):
        xp = g0 - D * (i / 8.0)              # scan X' from the cap down to 100 dX' below it, step dX'/8
        gdiff = h_comp(xp + D, nb_) - h_comp(xp, nb_)
        if gdiff > best_[0]:
            best_ = (gdiff, xp)
    # also the instance region, far from the cap
    print(f"Bitstring Compression ceiling at n={n}: num_blocks={nb_}, v={v_}, sigma_max={float(smax):.4g}, dX' <= {D:.3e}, G(1/64)={g0:.17g}; max over X' of H(X'+dX')-H(X') = {best_[0]:.4e} bit at X' = {best_[1]:.10g} (cap - {(g0-best_[1])/D:.1f} dX')")
print()
print("done")
