#!/usr/bin/env python3
"""Construct inputs that revisit MultiMMC 'orphan' contexts (present at a deep order,
absent at a shallower order because the shallower dictionary filled first).
phase X: (A c yA B c yB n)^RX gives order 16 a scoreboard lead (orders<=15 see c ambiguously)
phase A: random bytes from {48..255} that fill orders 3..16 (MAX_ENTRIES)
tail   : Z (window around the fill boundary) repeated RT times, each rep followed by a noise byte
"""
import random, sys
from fillsteps import fill_steps
def build(seed=1, RX=1000, LA=100200, pre=16, post=14, RT=1000, noise=True):
    r = random.Random(seed)
    c = list(range(1, 16)); A, B, yA, yB = 16, 17, 18, 19
    X = []
    for _ in range(RX):
        X += [A] + c + [yA] + [B] + c + [yB] + ([r.choice((20, 21))] if noise else [])
    Aph = [r.randrange(48, 256) for _ in range(LA)]
    S = X + Aph
    full = fill_steps(bytes(S))
    f = min(full[d] for d in range(3, 17))           # spec step (1-idx) when the first order in 3..16 fills
    # orphan pairs are added at steps f+1 .. full[16]; their y is s_{i-1} -> 0-idx position i-2
    first_orphan_y = f + 1 - 2
    last_orphan_y = full[16] - 2
    Z = S[first_orphan_y - pre:last_orphan_y + 1]
    tail = []
    for _ in range(RT):
        tail += Z + ([r.randrange(22, 32)] if noise else [])
    return S + tail, full, f, len(Z)
if __name__ == '__main__':
    seed, RX, RT, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    noise = (len(sys.argv) < 6 or sys.argv[5] != 'nonoise')
    S, full, f, lz = build(seed, RX, RT=RT, noise=noise)
    open(out, 'wb').write(bytes(S))
    print('len', len(S), 'fill', full[2:], 'first-full', f, 'lenZ', lz)
