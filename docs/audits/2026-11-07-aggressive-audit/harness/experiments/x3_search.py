#!/usr/bin/env python3
"""Search X3 construction variants with the two validated models at a scaled cap.
Variants: period P, boundary b, pre-roll q (copy of W's last q symbols before period 1),
and random W over {1..8} with all cyclic 3-grams distinct (2-gram repeats allowed = free
depth-2 ambiguity gadgets).  Reports steady-state per-period (text - cpp) correct counts."""
import sys, os, json
sys.path.insert(0, "/Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/harness/experiments")
import common
import x3_multimmc_orphans as x3

CAP = 3000
TOTAL = 20000

def random_word(P, label):
    ks = common.keystream(label, 64 * P + 64)
    k = 8
    def ok(w):
        tri = set()
        n = len(w)
        for i in range(n):
            t = (w[i], w[(i + 1) % n], w[(i + 2) % n])
            if t in tri:
                return False
            tri.add(t)
        return True
    # DFS with keystream-ordered candidates, cyclic 3-gram distinctness
    order = [[1 + (int(ks[i]) + j) % k for j in range(k)] for i in range(P + 1)]
    def dfs(w, tri):
        if len(w) == P:
            # closing 3-grams
            t1 = (w[-2], w[-1], w[0]); t2 = (w[-1], w[0], w[1])
            if t1 in tri or t2 in tri or t1 == t2:
                return None
            return w
        for c in order[len(w)]:
            if len(w) < 2:
                r = dfs(w + [c], tri)
                if r: return r
                continue
            t = (w[-2], w[-1], c)
            if t in tri: continue
            tri.add(t)
            r = dfs(w + [c], tri)
            if r: return r
            tri.discard(t)
        return None
    return dfs([], set())

def build(P, b, q, w, label):
    lf = CAP + 1 - b - q
    fill = x3.fill_all_3grams_distinct(lf, f"{label}/fill")
    pre = w[P - q:] if q else []
    tail_len = TOTAL - lf - q
    tail = (w * (tail_len // P + 2))[:tail_len]
    S = fill + pre + tail
    assert len(S) == TOTAL
    return S, lf + q   # start of period 1

def per_period(S, start, P, txt, cpp, first=3, last=None):
    nper = (len(S) - start) // P
    last = last or nper - 1
    tcount = ccount = 0
    for per in range(first, last):
        base = start + per * P
        for t in range(P):
            i = base + t - 2
            if 0 <= i < len(txt["correct"]):
                tcount += txt["correct"][i]
                ccount += cpp["correct"][i]
    n = last - first
    return tcount / n, ccount / n, n

results = []
for P in (32, 40, 48):
    for b in (17, 20, 25):
        if b + 15 > P: continue
        for q in (0, 4, 8, 12, 15):
            for seed in range(4):
                w = random_word(P, f"w{P}-{seed}")
                if w is None: continue
                d2 = len(set((w[i], w[(i+1) % P]) for i in range(P)))
                S, start = build(P, b, q, w, f"v-{P}-{b}-{q}-{seed}")
                txt = x3.mmc_text(S, max_entries=CAP)
                cpp = x3.mmc_cpp(S, max_entries=CAP)
                tp, cpv, n = per_period(S, start, P, txt, cpp)
                r = dict(P=P, b=b, q=q, seed=seed, distinct_2grams=d2, text_per_period=round(tp, 3),
                         cpp_per_period=round(cpv, 3), gap_text_minus_cpp=round(tp - cpv, 3),
                         C_text=txt["C"], C_cpp=cpp["C"], r_text=txt["r"], r_cpp=cpp["r"],
                         winner_text=txt["winner"], winner_cpp=cpp["winner"], periods=n)
                results.append(r)
                print(json.dumps(r))
results.sort(key=lambda r: -r["gap_text_minus_cpp"])
print("TOP 8 (largest text - cpp, i.e. overstating direction):")
for r in results[:8]:
    print(json.dumps(r))
print("BOTTOM 3:")
for r in results[-3:]:
    print(json.dumps(r))
