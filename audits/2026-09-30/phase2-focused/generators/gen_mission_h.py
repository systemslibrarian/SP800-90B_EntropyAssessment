#!/usr/bin/env python3
"""Regenerate the Mission H resource-test inputs byte-for-byte. Usage: python3 gen_mission_h.py <outdir>"""
import random, sys, os
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
r = random.Random(5)
open(os.path.join(out, 'u4in8_1e6.bin'), 'wb').write(bytes(r.randrange(16) for _ in range(10**6)))
open(os.path.join(out, 'fair_1e7.bin'), 'wb').write(bytes(r.getrandbits(1) for _ in range(10**7)))
open(os.path.join(out, 'u8_4e6.bin'), 'wb').write(r.randbytes(4 * 10**6))
