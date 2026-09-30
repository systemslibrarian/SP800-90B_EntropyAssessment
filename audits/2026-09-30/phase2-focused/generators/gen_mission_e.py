#!/usr/bin/env python3
"""Regenerate the Mission E oracle datasets byte-for-byte. Needs r1.bin and r8.bin from gen_w.py.
Usage: python3 gen_mission_e.py <dir-with-r1.bin-r8.bin> <outdir>"""
import random, sys, os
wdir, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
P = lambda n: os.path.join(out, n)
r = random.Random(9090)
L = 10**6
fair = open(os.path.join(wdir, 'r1.bin'), 'rb').read()
u8 = open(os.path.join(wdir, 'r8.bin'), 'rb').read()
b09 = bytes(1 if r.random() < 0.9 else 0 for _ in range(L))
sk3 = bytes(r.choices([0, 1, 2], weights=[0.7, 0.2, 0.1])[0] for _ in range(L))
for name, data in {'fair': fair, 'b09': b09, 'sk3': sk3, 'u8': u8}.items():
    for n in (64, 4096, L):
        open(P(f'{name}_{n}.bin'), 'wb').write(data[:n])
open(P('bij01_1000000.bin'), 'wb').write(fair)
open(P('bij17_1000000.bin'), 'wb').write(bytes(17 if x == 0 else 201 for x in fair))
open(P('two0255_1000000.bin'), 'wb').write(bytes(0 if x == 0 else 255 for x in fair))
