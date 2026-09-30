#!/usr/bin/env python3
"""Orphan construction v3 = v2 + a 'gadget' that gives orders >=5 a scoreboard lead over orders <=4
without creating a dictionary surplus between orders >=4 (see report)."""
import random, sys
from fillsteps import fill_steps
from orphgen2 import mkW
def build(seed, pos, RT, Wcut=30, gadget_pre=4, n=40, post=2000):
    r = random.Random(seed)
    x = [5, 6, 7, 8]; p1, p2, yA, yB = 9, 10, 11, 12
    cyc = [p1] + x + [yA] + [p2] + x + [yB]
    G = cyc * gadget_pre
    A1 = [r.randrange(16, 256) for _ in range(pos - len(G) - 5000)]
    A1b = [r.randrange(16, 256) for _ in range(5000)]
    W = mkW(r, n)
    A2 = [r.randrange(16, 256) for _ in range(post)]
    S = A1 + G + A1b + W + A2
    full = fill_steps(bytes(S))
    tail = []
    for _ in range(RT):
        tail += cyc + W[:Wcut] + [r.randrange(13, 16)]
    return S + tail, full, len(A1) + len(G) + len(A1b)
if __name__ == '__main__':
    seed, pos, RT, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    S, full, wpos = build(seed, pos, RT)
    open(out, 'wb').write(bytes(S))
    f = min(full[d] for d in range(3, 17))
    print('len', len(S), 'W at', wpos, 'fill d=2..16', full[2:], 'first-full step', f, '-> W offset of first orphan y', f + 1 - 2 - wpos)
