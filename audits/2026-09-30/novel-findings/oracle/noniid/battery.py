#!/usr/bin/env python3
"""Differential battery: tool (unmodified headers via harness) vs literal ref90b on crafted inputs."""
import os
import random
import sys

import cmp

D = os.path.dirname(os.path.abspath(__file__)) + '/data/bat'
os.makedirs(D, exist_ok=True)


def w(name, vals):
    p = f'{D}/{name}.bin'
    open(p, 'wb').write(bytes(vals))
    return p


def gen():
    R = random.Random(20260930)
    cases = []
    # 1. iid random, various alphabets; raw values scattered (translation exercised)
    for k in (3, 4, 5, 7, 16, 64, 256):
        vals = R.sample(range(256), k) if k < 256 else list(range(256))
        cases.append((f'iid_k{k}', [R.choice(vals) for _ in range(6000)], 8))
    # 2. strongly dependent Markov chains
    for k in (3, 5, 8):
        T = [[R.random() ** 4 for _ in range(k)] for _ in range(k)]
        s = 0
        out = []
        for _ in range(8000):
            tot = sum(T[s]); u = R.random() * tot; a = 0
            for y in range(k):
                a += T[s][y]
                if u <= a:
                    break
            s = y; out.append(s * 7 % 256)
        cases.append((f'markov_k{k}', out, 8))
    # 3. periodic with noise (periods around Lag D=128 and MCW windows)
    for P in (3, 17, 64, 127, 128, 129, 255, 256):
        base = [R.randrange(6) for _ in range(P)]
        out = [base[i % P] if R.random() > 0.05 else R.randrange(6) for i in range(9000)]
        cases.append((f'periodic_P{P}', out, 8))
    # 4. tie-heavy: rotating equal-count blocks, exact alternations
    cases.append(('tie_rot3', [(i // 21) % 3 for i in range(9000)], 8))
    cases.append(('tie_alt012', [i % 3 for i in range(9000)], 8))
    cases.append(('tie_blocks', [((i // 63) + (i % 2)) % 4 for i in range(9000)], 8))
    cases.append(('tie_pairs', [(0, 1, 1, 0, 2, 2, 0, 0, 1, 2, 1, 2)[i % 12] for i in range(9000)], 8))
    # 5. long runs interleaved with noise -> large r
    out = []
    while len(out) < 9000:
        out += [R.randrange(4)] * R.choice((1, 2, 50, 300)) + [R.randrange(4) for _ in range(R.randrange(20))]
    cases.append(('runs', out[:9000], 8))
    # 6. counters / gray code
    cases.append(('counter8', [i % 256 for i in range(9000)], 8))
    cases.append(('gray8', [(i ^ (i >> 1)) % 256 for i in range(9000)], 8))
    cases.append(('counter_mod5', [(i * 3) % 5 for i in range(9000)], 8))
    # 7. drifting MCV (window-sensitive)
    out = []
    for b in range(30):
        mcv = b % 5
        out += [mcv if R.random() < 0.4 else R.randrange(5) for _ in range(300)]
    cases.append(('drift5', out, 8))
    # 8. narrow widths 2..7 with full alphabets
    for bits in range(2, 8):
        cases.append((f'w{bits}', [R.randrange(1 << bits) for _ in range(5000)], bits))
    return cases


if __name__ == '__main__':
    do_bits = '--bits' in sys.argv
    total_bad = 0
    for name, vals, bits in gen():
        p = w(name, vals)
        bad = cmp.compare(p, bits, do_bitstring=do_bits, quiet=True)
        total_bad += len(bad)
        print(f'{name}: {"OK" if not bad else "MISMATCH " + repr(bad)}', flush=True)
    print('TOTAL MISMATCHES', total_bad)
