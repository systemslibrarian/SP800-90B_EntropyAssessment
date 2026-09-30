#!/usr/bin/env python3
"""Regenerate the phase-2 w/ datasets byte-for-byte (seeds/order exactly as used on 2026-09-30).
Usage: python3 gen_w.py <outdir>"""
import random, sys, os
out = sys.argv[1] if len(sys.argv) > 1 else '.'; os.makedirs(out, exist_ok=True)
P = lambda n: os.path.join(out, n)
# restart / general datasets (one RNG stream, seed 1, in this order)
r = random.Random(1)
open(P('r8.bin'), 'wb').write(bytes(r.randrange(256) for _ in range(10**6)))
open(P('r1.bin'), 'wb').write(bytes(r.randrange(2) for _ in range(10**6)))
open(P('r4.bin'), 'wb').write(bytes(r.randrange(16) for _ in range(10**6)))
open(P('zero.bin'), 'wb').write(bytes(10**6))
open(P('empty.bin'), 'wb').write(b'')
open(P('s999.bin'), 'wb').write(bytes(r.randrange(256) for _ in range(999000)))
open(P('s1001.bin'), 'wb').write(bytes(r.randrange(256) for _ in range(1001000)))
row = [r.randrange(256) for _ in range(1000)]
open(P('identrows.bin'), 'wb').write(bytes(row * 1000))
m = [r.randrange(256) for _ in range(10**6)]
for i in range(1000): m[i * 1000 + 5] = 7
open(P('hotcol.bin'), 'wb').write(bytes(m))
# N-01 rediscovery: IID Bernoulli(0.002), L = 1e6 (spec m = 1)
r = random.Random(20260930)
open(P('iid_p002.bin'), 'wb').write(bytes(1 if r.random() < 0.002 else 0 for _ in range(10**6)))
# R-1 rediscovery: exactly balanced alphabets (#246 assert for k = 3, 6, 7, 12)
r = random.Random(7)
for k, L in [(3, 1000002), (5, 1000000), (6, 1000002), (7, 1000006), (10, 1000000), (12, 1000008)]:
    a = [i % k for i in range(L)]; r.shuffle(a)
    open(P(f'bal_k{k}.bin'), 'wb').write(bytes(a))
