#!/usr/bin/env python3
"""F09 reproduction at the shipped MAX_ENTRIES=100,000 (generic MultiMMC, 8-bit literal path).
A1: random bytes {16..255} fill MultiMMC orders 3..16, then order 2 (spec order 2 = 2-symbol context).
Y : 36 bytes over {1..8} with all bigrams distinct (order-2 contexts deterministic, order-1 ambiguous);
    placed so that the order-2 dictionary becomes full inside Y (the "boundary").
tail: Y repeated R times.  In the tail the order-2 sub-predictor is the winner; it is correct up to
the boundary, then its context is absent (Null) for the rest of Y and the seam, then correct again.
Spec 6.3.9: Null => correct=0 => run broken every repetition.  Tool: run never reset."""
import random, sys
from fillsteps import fill_steps
def mkY(r, n=36):
    while True:
        Y = [r.randrange(1, 9) for _ in range(n)]
        bg = [tuple(Y[i:i+2]) for i in range(n - 1)] + [(Y[-1], Y[0])]
        if len(set(bg)) == len(bg): return Y
def build(seed, n1, R, target_off=24):
    r = random.Random(seed)
    A1 = [r.randrange(16, 256) for _ in range(n1 + 400)]
    Y = mkY(r)
    A2 = [r.randrange(16, 256) for _ in range(3000)]
    for _ in range(6):
        S = A1[:n1] + Y + A2
        full = fill_steps(bytes(S))
        yidx = full[2] - 2            # 0-idx of y of the last pair added to order 2
        off = yidx - n1
        if off == target_off: break
        n1 += off - target_off
    return A1[:n1] + Y + A2 + Y * R, full, n1, off
if __name__ == '__main__':
    seed, R, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    S, full, n1, off = build(seed, 100000, R)
    open(out, 'wb').write(bytes(S))
    print('len', len(S), 'Y at', n1, 'order-2 boundary at Y offset', off, 'fill steps d=2..16', full[2:])
