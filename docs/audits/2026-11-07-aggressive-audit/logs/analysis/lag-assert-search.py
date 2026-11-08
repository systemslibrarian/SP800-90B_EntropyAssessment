#!/usr/bin/env python3
"""Search for a tiny input on which predictionEstimate's guard call
prediction_estimate_function(curMax, r, N) (utils.h:1087-1109) reaches the
exterior root x = 1/p (p > r/(r+1)) and the live assert(p*x <= 1.0L) at :1105
(or assert(x >= xlast) at :1103) would fire.  Simulated in IEEE double, which
is what `long double` is on Darwin arm64; both the plain and the FMA-contracted
form of :1101 are evaluated.  Writes logs/analysis-lag-assert-search.log and
candidate inputs to corpus/.  Reuses the spec transcription in lag-probe.py."""
import math, os, sys, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lag_probe import lag_counts  # noqa
ZALPHA = 2.5758293035489008
EPS = 2.0 ** -52           # LDBL_EPSILON on Darwin arm64 (long double == double)

def pprime(C, N):
    pg = C / N
    if pg > 0:
        return min(1.0, pg + ZALPHA * math.sqrt((pg * (1.0 - pg)) / (N - 1.0)))
    return 1.0 - 0.01 ** (1.0 / N)

def simulate(p, r, N, fma):
    """Mirror utils.h:1087-1108 step by step. Returns dict of what happens."""
    q = 1.0 - p
    x = 1.0; xlast = 0.0; i = 0
    res = {"assert_x_ge_xlast": True, "assert_px_le_1": True, "iters": 0}
    while i <= 65 and (x - xlast) > EPS * x:
        xlast = x
        a = q * math.pow(p, r)
        b = math.pow(x, r + 1.0)
        x = math.fma(a, b, 1.0) if fma else 1.0 + a * b
        i += 1
        if not (x >= xlast):
            res["assert_x_ge_xlast"] = False; res["iters"] = i; return res
        if not (p * x <= 1.0):
            res["assert_px_le_1"] = False; res["iters"] = i; res["p_times_x"] = p * x; return res
    res["iters"] = i
    one_minus_px = math.fma(-p, x, 1.0) if fma else 1.0 - p * x
    res["one_minus_px"] = one_minus_px
    res["f"] = (math.log(one_minus_px) if one_minus_px > 0 else (-math.inf if one_minus_px == 0 else float('nan')))
    res["x"] = x; res["p_times_x"] = p * x; res["inv_p"] = 1.0 / p
    return res

here = os.path.dirname(os.path.abspath(__file__)); audit = os.path.abspath(os.path.join(here, "..", ".."))
corpus = os.path.join(audit, "corpus"); logs = os.path.join(audit, "logs")
out = []
L = 20000
base = [i & 1 for i in range(L)]           # alternating 0101...: lag 2 perfect after warm-up
hits = []
for G in range(3, 9):                       # glitches (single bit flips)
    for phase in range(0, 10):
        for spread in (0, 1, 2, 3):
            S = base[:]
            step = L // (G + 1)
            pos = [step * (g + 1) + phase * 37 + spread * g * 101 for g in range(G)]
            pos = [p for p in pos if 200 < p < L - 200]
            for p_ in pos: S[p_] ^= 1
            C, r, N, _ = lag_counts(S)
            p = pprime(C, N)
            if not (p < 1.0): continue
            thresh = r / (r + 1.0)
            plain = simulate(p, r, N, False); fma = simulate(p, r, N, True)
            tag = "G=%d phase=%d spread=%d pos=%s" % (G, phase, spread, pos)
            line = "%s | C=%d r=%d N=%d W=%d p=%.17g r/(r+1)=%.17g p>thr=%s rate=%.3f | plain: px<=1 %s x>=xl %s it=%d px=%r | fma: px<=1 %s x>=xl %s it=%d px=%r" % (
                tag, C, r, N, N - C, p, thresh, p > thresh, (r + 1) * (1 - p),
                plain["assert_px_le_1"], plain["assert_x_ge_xlast"], plain["iters"], plain.get("p_times_x"),
                fma["assert_px_le_1"], fma["assert_x_ge_xlast"], fma["iters"], fma.get("p_times_x"))
            out.append(line)
            if (not plain["assert_px_le_1"]) or (not plain["assert_x_ge_xlast"]) or (not fma["assert_px_le_1"]) or (not fma["assert_x_ge_xlast"]):
                hits.append((tag, S, C, r, N, p, plain, fma))
out.append("")
out.append("constructions predicted to trip a live assert: %d of %d evaluated" % (len(hits), len([l for l in out if l.startswith('G=')])))
# write up to 3 predicted-abort inputs and 1 predicted-pass control (same family)
written = []
for k, (tag, S, C, r, N, p, plain, fma) in enumerate(hits[:3]):
    name = "lag-assert-cand%d-1bit-20000.bin" % (k + 1)
    path = os.path.join(corpus, name); open(path, "wb").write(bytes(S))
    written.append((name, tag, C, r, N, p, hashlib.sha256(bytes(S)).hexdigest(), "PREDICTED ABORT plain=%s fma=%s" % (plain["assert_px_le_1"] and plain["assert_x_ge_xlast"], fma["assert_px_le_1"] and fma["assert_x_ge_xlast"])))
# control: a sibling construction predicted to pass both asserts, with p > r/(r+1) if possible
ctrl = None
for G in range(3, 9):
    for phase in range(0, 10):
        for spread in (0, 1, 2, 3):
            S = base[:]; step = L // (G + 1)
            pos = [step * (g + 1) + phase * 37 + spread * g * 101 for g in range(G)]
            pos = [p for p in pos if 200 < p < L - 200]
            for p_ in pos: S[p_] ^= 1
            C, r, N, _ = lag_counts(S); p = pprime(C, N)
            if not (p < 1.0): continue
            plain = simulate(p, r, N, False); fma = simulate(p, r, N, True)
            if plain["assert_px_le_1"] and plain["assert_x_ge_xlast"] and fma["assert_px_le_1"] and fma["assert_x_ge_xlast"] and p > r / (r + 1.0):
                ctrl = (S, "G=%d phase=%d spread=%d pos=%s" % (G, phase, spread, pos), C, r, N, p); break
        if ctrl: break
    if ctrl: break
if ctrl:
    S, tag, C, r, N, p = ctrl
    name = "lag-assert-control-1bit-20000.bin"; path = os.path.join(corpus, name); open(path, "wb").write(bytes(S))
    written.append((name, tag, C, r, N, p, hashlib.sha256(bytes(S)).hexdigest(), "PREDICTED PASS (p > r/(r+1) but rounding lands at or below 1)"))
out.append("")
for w in written:
    out.append("WROTE %s  %s  C=%d r=%d N=%d p=%.17g sha256=%s  %s" % w)
open(os.path.join(logs, "analysis-lag-assert-search.log"), "w").write("\n".join(out) + "\n")
print("\n".join(out[-(len(written) + 3):]))
print("hits:", len(hits))
for h in hits[:6]:
    print("  ", h[0], "C=%d r=%d p=%.17g" % (h[2], h[3], h[5]), "plain:", h[6], "fma:", h[7])
