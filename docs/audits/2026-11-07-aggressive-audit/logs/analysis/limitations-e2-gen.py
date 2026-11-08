#!/usr/bin/env python3
"""Regenerates the three LIMITATIONS-DRAFT.md section 4 inputs (intake.md section 4, E2).

Bits form a first-order chain P(b_t = b_{t-1}) = 0.9 across symbol boundaries; seven
chain bits per symbol, MSB first.  Three files, 20,000 samples each:
  limitations-e2-chain-7bit-20000.bin        the 7-bit values            (declare 7)
  limitations-e2-chain-lsb0-8bit-20000.bin   the same values << 1, bit 0 stuck at 0 (declare 8)
  limitations-e2-chain-1bit-20000.bin        the first 20,000 chain bits (declare 1)

usage: limitations-e2-gen.py <output-directory>
Expected sha256 (recorded in LIMITATIONS-DRAFT.md section 4):
  6628ee79bef462f4838bcd6817a29f7ed40f0c59c006f9dd26d68334b970c4d3  7bit
  d6fc18eb91eabecf145ce069a2ad3af4b05b4a8b92d8ed4a94de0b36114ccf2e  lsb0-8bit
  745643b13f8364dac061c9819a498092777ab2f1e34cd814a27bbe8938b1698f  1bit
"""
import hashlib
import math
import os
import random
import sys

if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
    sys.exit(__doc__)
out = sys.argv[1]
rng = random.Random(20261107)
nsym = 20000
bits = [rng.randrange(2)]
while len(bits) < 7 * nsym:
    bits.append(bits[-1] if rng.random() < 0.9 else 1 - bits[-1])
vals7 = []
for i in range(nsym):
    v = 0
    for j in range(7):
        v = (v << 1) | bits[7 * i + j]
    vals7.append(v)
files = {
    "limitations-e2-chain-7bit-20000.bin": bytes(vals7),
    "limitations-e2-chain-lsb0-8bit-20000.bin": bytes(v << 1 for v in vals7),
    "limitations-e2-chain-1bit-20000.bin": bytes(bits[:20000]),
}
for name, data in files.items():
    with open(os.path.join(out, name), "wb") as f:
        f.write(data)
    print(hashlib.sha256(data).hexdigest(), name, len(data))
print("truth: conditional min-entropy per 7-bit symbol = -log2(0.9^7) = %.6f" % (-math.log2(0.9 ** 7)))
print("truth: unconditional min-entropy per 7-bit symbol = -log2(0.5*0.9^6) = %.6f" % (-math.log2(0.5 * 0.9 ** 6)))
print("truth: per chain bit = -log2(0.9) = %.6f" % (-math.log2(0.9)))
same = sum(1 for i in range(1, len(bits)) if bits[i] == bits[i - 1])
print("empirical P(stay) = %.5f over %d transitions" % (same / (len(bits) - 1), len(bits) - 1))
