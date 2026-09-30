#!/usr/bin/env python3
"""Orphan construction v2: random fill over {16..255}; a crafted window W over {1,2,3,4}
(all 4-strings unique) is placed so that the MultiMMC fill boundary (first full order in 3..16)
falls inside W; the tail repeats W (+ optional noise byte) so that orphan contexts recur while
orders 1-2 are ambiguous on W."""
import random, sys
from fillsteps import fill_steps
def mkW(r, n):
    while True:
        W = [r.randrange(1, 5) for _ in range(n)]
        q = [tuple(W[i:i+4]) for i in range(n - 3)]
        if len(set(q)) == len(q): return W
def build(seed, pos, n=40, post=2000, RT=2000, noise=True):
    r = random.Random(seed)
    A1 = [r.randrange(16, 256) for _ in range(pos)]
    W = mkW(r, n)
    A2 = [r.randrange(16, 256) for _ in range(post)]
    S = A1 + W + A2
    full = fill_steps(bytes(S))
    tail = []
    for _ in range(RT):
        tail += W + ([r.randrange(5, 16)] if noise else [])
    return S + tail, full
if __name__ == '__main__':
    seed, pos, RT, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    noise = not (len(sys.argv) > 5 and sys.argv[5] == 'nonoise')
    S, full = build(seed, pos, RT=RT, noise=noise)
    open(out, 'wb').write(bytes(S))
    f = min(full[d] for d in range(3, 17))
    print('len', len(S), 'W at 0-idx', pos, '..', pos + 39, 'fill steps (spec i) d=2..16', full[2:], 'first-full', f, '-> y index', f - 2)
