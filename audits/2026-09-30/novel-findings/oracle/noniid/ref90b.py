#!/usr/bin/env python3
"""Literal SP 800-90B (Jan 2018) section 6.3.7-6.3.10 reference implementation.

Written from the spec pseudocode (1-indexed in the spec; comments give the spec
step), NOT from the tool's source.  Each estimator keeps the spec's structure:
separate "update dictionary" and "predict" phases, a `correct` array, and the
longest run computed from that array afterwards.

Tie-break conventions that the spec text leaves to the implementer or that could
not be re-read (spec PDF not in the workspace) are parameters:
  mmc_tie / lz_tie : 'largest' (largest symbol value wins a count tie; the tool's
                     convention) or 'smallest'.
MultiMCW ties: spec 6.3.7 step 3a: most recently occurring among the most frequent.
"""
import sys
from collections import defaultdict

import mpmath

mpmath.mp.dps = 60
ZALPHA_TOOL = 2.5758293035489008
ZALPHA_SPEC = 2.576

NULL = None


def longest_run(correct):
    best = cur = 0
    for c in correct:
        if c:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


# ---------------------------------------------------------------- 6.3.7
def multi_mcw(S, k=None):
    """6.3.7.  numpy is used only to count window contents; the argmax/tie rule is
    evaluated from scratch at every step (no incremental 'frequent' tracking)."""
    import numpy as np
    L = len(S)
    W = [63, 255, 1023, 4095]
    D = 4
    N = L - W[0]
    if k is None:
        k = max(S) + 1
    correct = [0] * N
    scoreboard = [0] * D
    winner = 0  # spec winner = 1
    cnt = np.zeros((D, k), dtype=np.int64)
    last = np.full((D, k), -1, dtype=np.int64)  # most recent position inside the window
    Sarr = np.asarray(S, dtype=np.int64)
    # window j holds s_{i-w_j} .. s_{i-1} (1-indexed) = S[i-1-w_j : i-1] (0-indexed)
    for i1 in range(W[0] + 1, L + 1):          # spec: for i = w1+1 to L
        i0 = i1 - 1                             # 0-index of s_i
        frequent = [NULL] * D
        for j in range(D):
            if i1 > W[j]:
                lo = i0 - W[j]
                # rebuild counts only when the window first becomes valid, then slide
                if i1 == W[j] + 1:
                    cnt[j, :] = np.bincount(Sarr[lo:i0], minlength=k)
                    for p in range(lo, i0):
                        last[j, S[p]] = p
                # argmax over count, tie -> most recent occurrence
                key = cnt[j] * (L + 2) + last[j]
                frequent[j] = int(np.argmax(key))
        prediction = frequent[winner]
        if prediction is not NULL and prediction == S[i0]:
            correct[i1 - W[0] - 1] = 1
        for j in range(D):
            if frequent[j] is not NULL and frequent[j] == S[i0]:
                scoreboard[j] += 1
                if scoreboard[j] >= scoreboard[winner]:
                    winner = j
        # slide windows to s_{i+1-w_j} .. s_i for the next step
        for j in range(D):
            if i1 > W[j]:
                out = S[i0 - W[j]]
                cnt[j, out] -= 1
                cnt[j, S[i0]] += 1
                last[j, S[i0]] = i0
            elif i1 + 1 > W[j] and i1 + 1 == W[j] + 1:
                pass  # built lazily above
    C = sum(correct)
    return C, N, longest_run(correct) + 1, k


# ---------------------------------------------------------------- 6.3.8
def lag(S, k=None):
    L = len(S)
    D = 128
    N = L - 1
    if k is None:
        k = max(S) + 1
    correct = [0] * N
    scoreboard = [0] * (D + 1)
    winner = 1
    for i in range(2, L + 1):  # spec 1-indexed
        s = lambda t: S[t - 1]
        lagv = [NULL] * (D + 1)
        for d in range(1, D + 1):
            if d < i:
                lagv[d] = s(i - d)
        prediction = lagv[winner]
        if prediction is not NULL and prediction == s(i):
            correct[i - 2] = 1
        for d in range(1, D + 1):
            if lagv[d] is not NULL and lagv[d] == s(i):
                scoreboard[d] += 1
                if scoreboard[d] >= scoreboard[winner]:
                    winner = d
    C = sum(correct)
    return C, N, longest_run(correct) + 1, k


# ---------------------------------------------------------------- 6.3.9
def _argmax_y(counts, tie):
    best_y, best_c = None, -1
    for y, c in counts.items():
        if c > best_c or (c == best_c and ((tie == 'largest' and y > best_y) or (tie == 'smallest' and y < best_y))):
            best_y, best_c = y, c
    return best_y, best_c


def multi_mmc(S, k=None, D=16, max_entries=100000, tie='largest', trace=None):
    L = len(S)
    N = L - 2
    if k is None:
        k = max(S) + 1
    correct = [0] * N
    entries = [0] * (D + 1)
    M = [None] + [dict() for _ in range(D)]  # M[d][x] = {y: count}
    scoreboard = [0] * (D + 1)
    winner = 1
    nulls_by_winner = 0
    s = lambda t: S[t - 1]
    for i in range(3, L + 1):
        # step 4a: update with (s_{i-d-1..i-2}) -> s_{i-1}
        for d in range(1, D + 1):
            if d < i - 1:
                x = tuple(S[i - d - 2:i - 2])
                y = s(i - 1)
                md = M[d]
                if x in md and y in md[x]:
                    md[x][y] += 1
                elif entries[d] < max_entries:
                    md.setdefault(x, {})[y] = 1
                    entries[d] += 1
        # step 4b: sub-predictions, each order independently
        sub = [NULL] * (D + 1)
        for d in range(1, D + 1):
            if d < i:
                x = tuple(S[i - d - 1:i - 1])
                cnts = M[d].get(x)
                if cnts:
                    sub[d] = _argmax_y(cnts, tie)[0]
        prediction = sub[winner]
        if prediction is NULL:
            nulls_by_winner += 1
        if prediction is not NULL and prediction == s(i):
            correct[i - 3] = 1
        for d in range(1, D + 1):
            if sub[d] is not NULL and sub[d] == s(i):
                scoreboard[d] += 1
                if scoreboard[d] >= scoreboard[winner]:
                    winner = d
        if trace is not None:
            trace.append((i, winner, prediction, correct[i - 3]))
    C = sum(correct)
    info = dict(entries=entries[1:], nulls_by_winner=nulls_by_winner, scoreboard=scoreboard[1:])
    return C, N, longest_run(correct) + 1, k, info


# ---------------------------------------------------------------- 6.3.10
def lz78y(S, k=None, B=16, max_dict=65536, tie='largest'):
    L = len(S)
    N = L - B - 1
    if k is None:
        k = max(S) + 1
    correct = [0] * N
    Dct = {}
    size = 0
    s = lambda t: S[t - 1]
    for i in range(B + 2, L + 1):
        # step 3a
        for j in range(B, 0, -1):
            prev = tuple(S[i - j - 2:i - 2])  # s_{i-j-1} .. s_{i-2}
            y = s(i - 1)
            if prev not in Dct and size < max_dict:
                Dct[prev] = {y: 0}
                size += 1
            if prev in Dct:
                Dct[prev][y] = Dct[prev].get(y, 0) + 1
        # step 3b/3c
        maxcount = 0
        prediction = NULL
        for j in range(B, 0, -1):
            prev = tuple(S[i - j - 1:i - 1])  # s_{i-j} .. s_{i-1}
            if prev in Dct:
                y, c = _argmax_y(Dct[prev], tie)
                if c > maxcount:
                    prediction = y
                    maxcount = c
        if prediction is not NULL and prediction == s(i):
            correct[i - B - 2] = 1
    C = sum(correct)
    return C, N, longest_run(correct) + 1, k, dict(dict_size=size)


# ---------------------------------------------------------------- 6.3.7 steps 5-7
def x10(p, r):
    q = 1 - p
    x = mpmath.mpf(1)
    for _ in range(10):
        x = 1 + q * p ** r * x ** (r + 1)
    return x


def local_f(p, r, N):
    p = mpmath.mpf(p)
    q = 1 - p
    x = x10(p, r)
    return (1 - p * x) / ((r + 1 - r * x) * q) / x ** (N + 1)


def pred_estimate(C, N, r, k, z=ZALPHA_TOOL):
    """r is spec r = longest run + 1."""
    C = mpmath.mpf(C)
    N_ = mpmath.mpf(N)
    pg = C / N_
    if C == 0:
        pgp = 1 - mpmath.mpf('0.01') ** (1 / N_)
    else:
        pgp = min(mpmath.mpf(1), pg + z * mpmath.sqrt(pg * (1 - pg) / (N_ - 1)))
    lo = max(pgp, mpmath.mpf(1) / k)
    plocal = None
    if lo < 1 and local_f(lo, r, N) > mpmath.mpf('0.99'):
        a, b = lo, mpmath.mpf(1) - mpmath.mpf(10) ** -40
        for _ in range(200):
            m = (a + b) / 2
            if local_f(m, r, N) > mpmath.mpf('0.99'):
                a = m
            else:
                b = m
        plocal = (a + b) / 2
    pmax = max(lo, plocal if plocal is not None else 0)
    return dict(C=int(C), N=N, r=r, Pglobal=float(pg), Pglobalp=float(pgp),
                Plocal=(float(plocal) if plocal is not None else None), H=float(-mpmath.log(pmax, 2)))


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    S = list(data)
    which = sys.argv[2:] or ['mcw', 'lag', 'mmc', 'lz']
    for w in which:
        if w == 'mcw':
            C, N, r, k = multi_mcw(S)
        elif w == 'lag':
            C, N, r, k = lag(S)
        elif w == 'mmc':
            C, N, r, k, info = multi_mmc(S)
        elif w == 'lz':
            C, N, r, k, info = lz78y(S)
        print(w, C, r, N)
