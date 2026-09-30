#!/usr/bin/env python3
"""Independent SP 800-90B single-estimator oracles, written from the PDF text only.

Usage: oracle.py <file> [bits]   -> prints "<estimator>: key = value" lines.
Estimators: MCV 6.3.1, Markov 6.3.3 (binary only), t-Tuple 6.3.5, LRS 6.3.6,
Lag 6.3.8, LZ78Y 6.3.10. Symbols are relabelled 0..k-1 in sorted order (the
spec's estimators only use equality/order, so this is the literal sequence).
"""
import sys, math
from collections import Counter

Z = 2.576  # the spec's printed Z(1-0.005); the tool uses 2.5758293035489008 (known #22)
ZT = 2.5758293035489008


def mcv(s, z):
    L = len(s)
    p = max(Counter(s).values()) / L
    pu = min(1.0, p + z * math.sqrt(p * (1 - p) / (L - 1)))
    return {'p-hat': p, 'p_u': pu, 'min entropy': -math.log2(pu)}


def markov(s):
    L = len(s)
    P0 = s.count(0) / L
    P1 = 1 - P0
    c = Counter(zip(s, s[1:]))
    n0 = c[(0, 0)] + c[(0, 1)]
    n1 = c[(1, 0)] + c[(1, 1)]
    P00 = c[(0, 0)] / n0 if n0 else 0.0
    P01 = c[(0, 1)] / n0 if n0 else 0.0
    P10 = c[(1, 0)] / n1 if n1 else 0.0
    P11 = c[(1, 1)] / n1 if n1 else 0.0
    def lg(x):
        return math.log2(x) if x > 0 else -math.inf
    cands = [lg(P0) + 127 * lg(P00), lg(P0) + 64 * lg(P01) + 63 * lg(P10),
             lg(P0) + lg(P01) + 126 * lg(P11), lg(P1) + lg(P10) + 126 * lg(P00),
             lg(P1) + 64 * lg(P10) + 63 * lg(P01), lg(P1) + 127 * lg(P11)]
    lpmax = max(cands)
    return {'P_0': P0, 'P_1': P1, 'P_{0,0}': P00, 'P_{0,1}': P01, 'P_{1,0}': P10,
            'P_{1,1}': P11, 'min entropy': min(-lpmax / 128, 1.0)}


def tuple_counts(b, W):
    """Counter of all overlapping W-tuples of bytes b."""
    return Counter(b[i:i + W] for i in range(len(b) - W + 1))


def ttuple_lrs(s, z):
    b = bytes(s)
    L = len(b)
    Q = {}
    W = 1
    while True:
        c = tuple_counts(b, W)
        Q[W] = max(c.values())
        if Q[W] < 35:
            break
        W += 1
    t = W - 1  # largest t with Q[t] >= 35
    u = W      # smallest u with Q[u] < 35
    out = {}
    if t >= 1:
        pmax = max((Q[i] / (L - i + 1)) ** (1.0 / i) for i in range(1, t + 1))
        pu = min(1.0, pmax + z * math.sqrt(pmax * (1 - pmax) / (L - 1)))
        out['t-Tuple'] = {'t': t, 'p-hat_max': pmax, 'p_u': pu, 'min entropy': -math.log2(pu)}
    # v: largest length with a repeat
    v = 0
    W = 1
    while True:
        c = tuple_counts(b, W)
        if max(c.values()) >= 2:
            v = W
            W += 1
        else:
            break
    if v < u:
        out['LRS'] = {'u': u, 'v': v, 'skip': 1}
        return out
    phat = 0.0
    for W in range(u, v + 1):
        c = tuple_counts(b, W)
        num = sum(ci * (ci - 1) // 2 for ci in c.values())
        den = (L - W + 1) * (L - W) // 2
        phat = max(phat, (num / den) ** (1.0 / W))
    pu = min(1.0, phat + z * math.sqrt(phat * (1 - phat) / (L - 1)))
    out['LRS'] = {'u': u, 'v': v, 'p-hat': phat, 'p_u': pu, 'min entropy': -math.log2(pu)}
    return out


def plocal(r, N):
    """Solve 0.99 = (1-p x)/((r+1-r x) q) * x^-(N+1), x = x_10 (spec), by bisection on p."""
    def f(p):
        q = 1 - p
        x = 1.0
        for _ in range(10):
            x = 1 + q * p ** r * x ** (r + 1)
        a = 1 - p * x
        bb = (r + 1 - r * x) * q
        if a <= 0 or bb <= 0:
            return None
        return math.log(a) - math.log(bb) - (N + 1) * math.log(x)
    lo, hi = 0.0, 1.0
    target = math.log(0.99)
    for _ in range(200):
        mid = (lo + hi) / 2
        v = f(mid)
        # f decreases with p (prob. of no run of length r falls as p rises)
        if v is None or v < target:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def pred_estimate(C, N, runlen, k, z):
    r = runlen + 1
    pg = C / N
    pgp = (1 - 0.01 ** (1.0 / N)) if C == 0 else min(1.0, pg + z * math.sqrt(pg * (1 - pg) / (N - 1)))
    pl = plocal(r, N)
    return {'C': C, 'r': r, 'N': N, "P_global'": pgp, 'P_local': pl,
            'min entropy': -math.log2(max(pgp, pl, 1.0 / k))}


def lag(s, k, z):
    D = 128
    L = len(s)
    score = [0] * (D + 1)
    winner = 1
    C = run = maxrun = 0
    for i in range(1, L):  # 0-indexed i; spec i = i+1
        si = s[i]
        pred = s[i - winner] if winner <= i else None
        if pred == si:
            C += 1; run += 1; maxrun = max(maxrun, run)
        else:
            run = 0
        for d in range(1, min(D, i) + 1):
            if s[i - d] == si:
                score[d] += 1
                if score[d] >= score[winner]:
                    winner = d
    return pred_estimate(C, L - 1, maxrun, k, z)


def lz78y(s, k, z):
    B = 16
    L = len(s)
    maxsize = 65536
    D = {}      # prefix tuple -> {symbol: count}
    best = {}   # prefix -> (count, symbol), counts only grow
    size = 0
    C = run = maxrun = 0
    for i in range(B + 1, L):  # 0-indexed; spec i = B+2..L
        # step a: update with s[i-1] after prefixes ending at s[i-2]
        for j in range(B, 0, -1):
            pre = tuple(s[i - j - 1:i - 1])
            if pre not in D and size < maxsize:
                D[pre] = {s[i - 1]: 0}; best[pre] = (0, s[i - 1]); size += 1
            if pre in D:
                d = D[pre]
                cnt = d.get(s[i - 1], 0) + 1
                d[s[i - 1]] = cnt
                bc, by = best[pre]
                if cnt > bc or (cnt == bc and s[i - 1] > by):
                    best[pre] = (cnt, s[i - 1])
        # step b: predict
        pred, maxc = None, 0
        for j in range(B, 0, -1):
            prev = tuple(s[i - j:i])
            if prev in D:
                bc, by = best[prev]
                if bc > maxc:
                    pred, maxc = by, bc
        if pred == s[i]:
            C += 1; run += 1; maxrun = max(maxrun, run)
        else:
            run = 0
    return pred_estimate(C, L - B - 1, maxrun, k, z)


def main():
    fn = sys.argv[1]
    which = sys.argv[2].split(',') if len(sys.argv) > 2 else ['MCV', 'Markov', 'TT', 'Lag', 'LZ78Y']
    z = ZT if (len(sys.argv) > 3 and sys.argv[3] == 'tool-z') else Z
    raw = open(fn, 'rb').read()
    alph = sorted(set(raw))
    m = {v: i for i, v in enumerate(alph)}
    s = [m[v] for v in raw]
    k = len(alph)
    res = {}
    if 'MCV' in which: res['Most Common Value'] = mcv(s, z)
    if 'Markov' in which and k == 2: res['Markov'] = markov(s)
    if 'TT' in which: res.update(ttuple_lrs(s, z))
    if 'Lag' in which: res['Lag Prediction'] = lag(s, k, z)
    if 'LZ78Y' in which: res['LZ78Y Prediction'] = lz78y(s, k, z)
    for est, kv in res.items():
        for key, val in kv.items():
            print(f"{est}: {key} = {val!r}")


if __name__ == '__main__':
    main()
