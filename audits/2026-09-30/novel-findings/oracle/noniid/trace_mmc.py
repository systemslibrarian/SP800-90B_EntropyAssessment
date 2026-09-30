#!/usr/bin/env python3
"""Side-by-side trace of spec MultiMMC vs tool-semantics (chained lookup, no reset on Null)."""
import sys
def run(S, M, chain, noreset, D=16):
    L = len(S); ent = [0]*(D+1); Md = [None]+[dict() for _ in range(D)]
    score = [0]*(D+1); win = 1; C = run_ = mx = 0; tr = []
    Md[1][tuple(S[0:1])] = {S[1]: 1}; ent[1] = 1
    for i in range(3, L+1):
        sub = [None]*(D+1); found = [False]*(D+1); ok = True
        for d in range(1, D+1):
            if d <= i-2 and (ok or not chain):
                x = tuple(S[i-d-1:i-1]); c = Md[d].get(x)
                if c:
                    found[d] = True; sub[d] = max(c.items(), key=lambda t: (t[1], t[0]))[0]
                else: ok = False
        pred = sub[win]; w0 = win
        if pred is not None and pred == S[i-1]:
            C += 1; run_ += 1; mx = max(mx, run_)
        elif pred is not None or not noreset: run_ = 0
        for d in range(1, D+1):
            if sub[d] is not None and sub[d] == S[i-1]:
                score[d] += 1
                if score[d] >= score[win]: win = d
        for d in range(1, D+1):
            if d <= i-1:
                x = tuple(S[i-d-1:i-1]); y = S[i-1]
                if found[d] or not chain:
                    c = Md[d].get(x)
                    if c is not None and y in c: c[y] += 1
                    elif ent[d] < M: Md[d].setdefault(x, {})[y] = 1; ent[d] += 1
                elif ent[d] < M:
                    Md[d].setdefault(x, {}); Md[d][x][y] = Md[d][x].get(y, 0) + 1; ent[d] += 1
        tr.append((i, w0, pred, S[i-1], run_, tuple(sub[1:6])))
    return C, mx+1, tr
if __name__ == '__main__':
    S = list(open(sys.argv[1], 'rb').read()); M = int(sys.argv[2])
    a = run(S, M, False, False); b = run(S, M, True, True)
    print('spec C,r', a[:2], ' tool-sem C,r', b[:2])
    n = 0
    for x, y in zip(a[2], b[2]):
        if x[1:3] != y[1:3]:
            print('i=%d spec(win=%d pred=%s) tool(win=%d pred=%s) actual=%d' % (x[0], x[1], x[2], y[1], y[2], x[3]))
            n += 1
            if n > 25: break
